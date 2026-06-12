#!/usr/bin/env python3
"""file3.py — Download models, generate SLM training data, fine-tune SmolLM2-135M, export GGUF.

Run on the server:
    uv run python file3.py

Inputs:
    server_artifacts/ml/entity_profiles.jsonl   (from file2.py)

Outputs (in server_artifacts/slm/):
    slm_training_data.jsonl     Teacher-generated (profile → narrative) examples
    lora_output/final_model/    Fine-tuned LoRA adapter
    gguf/smollm135m_taxnet.gguf  CPU-runnable quantized student model

The script is idempotent: completed stages are skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from server_utils import (
    download_if_missing,
    is_checkpoint_complete,
    log as _log,
    read_jsonl,
    save_checkpoint,
    write_jsonl,
)

# Optional progress bars
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover

    def tqdm(iterable=None, **kwargs):  # type: ignore[misc]
        return iterable


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAGE = "file3"

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "server_artifacts" / "slm"
MODELS_DIR = ROOT / "server_artifacts" / "models"
PROFILES_PATH = ROOT / "server_artifacts" / "ml" / "entity_profiles.jsonl"
TRAINING_DATA_PATH = ARTIFACTS_DIR / "slm_training_data.jsonl"
LORA_OUTPUT_DIR = ARTIFACTS_DIR / "lora_output"
GGUF_OUTPUT_DIR = ARTIFACTS_DIR / "gguf"

STUDENT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
TEACHER_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# Training hyperparameters
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.0
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
PER_DEVICE_BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4
MAX_SEQ_LENGTH = 1024
WARMUP_STEPS = 50

# Teacher generation
TEACHER_BATCH_SIZE = 16
MAX_NEW_TOKENS = 180
TEMPERATURE = 0.3
TOP_P = 0.9

# Training set size
MAX_TRAINING_EXAMPLES = 8_000
HIGH_RISK_BUDGET = 4_000
MEDIUM_RISK_BUDGET = 2_500
LOW_RISK_BUDGET = 1_500


def log(message: str) -> None:
    _log(STAGE, message)


# ---------------------------------------------------------------------------
# Model download
# ---------------------------------------------------------------------------


def download_model(repo_id: str, local_dir: Path, force: bool = False) -> Path:
    """Download a HuggingFace model snapshot to a local directory."""
    local_dir.mkdir(parents=True, exist_ok=True)
    if any(local_dir.iterdir()) and not force:
        log(f"  {repo_id} already downloaded at {local_dir}")
        return local_dir
    log(f"Downloading {repo_id} ...")
    snapshot_download(repo_id=repo_id, local_dir=str(local_dir), local_dir_use_symlinks=False)
    return local_dir


# ---------------------------------------------------------------------------
# Training data generation
# ---------------------------------------------------------------------------


def profile_to_text(profile: dict[str, Any]) -> str:
    """Convert an entity profile dict into a concise text block for the teacher."""
    lines = [
        f"Name: {profile.get('canonical_name') or 'Unknown'}",
        f"Risk score: {profile.get('risk_score', 0):.1f}",
        f"Proxy label: {profile.get('proxy_label', 0):.1f}",
        f"Record sources: {', '.join(profile.get('record_sources', []))}",
        f"Record count: {profile.get('record_count', 0)}",
    ]

    features = profile.get("features", {})
    if features:
        top_features = sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)[:8]
        lines.append("Top features:")
        for name, value in top_features:
            lines.append(f"  - {name}: {value:.3f}")

    indicators = profile.get("source_indicators", {})
    active_sources = [k.replace("source_", "") for k, v in indicators.items() if v]
    if active_sources:
        lines.append(f"Active source flags: {', '.join(active_sources)}")

    return "\n".join(lines)


TEACHER_SYSTEM_PROMPT = (
    "You are a Pakistani tax audit analyst writing concise, factual risk narratives. "
    "Given an entity profile, produce a 2-3 sentence audit narrative. "
    "Mention relevant Pakistan tax law sections only when you are confident. "
    "Do not invent facts not present in the profile. Be direct and professional."
)


def build_teacher_prompt(profile_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": TEACHER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Write a short audit narrative for the following entity profile:\n\n{profile_text}\n\nAudit narrative:",
        },
    ]


def clean_teacher_output(text: str) -> str:
    """Strip boilerplate and keep the narrative."""
    text = text.strip()
    # Remove common prefixes the model might emit
    for prefix in ("Audit narrative:", "Narrative:", "Assessment:"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix) :].strip()
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def sample_profiles_for_training(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sample a balanced-ish training set across risk tiers."""
    high = [p for p in profiles if p.get("risk_score", 0) > 60]
    medium = [p for p in profiles if 40 < p.get("risk_score", 0) <= 60]
    low = [p for p in profiles if p.get("risk_score", 0) <= 40]

    random.seed(42)
    high_sample = random.sample(high, min(HIGH_RISK_BUDGET, len(high)))
    medium_sample = random.sample(medium, min(MEDIUM_RISK_BUDGET, len(medium)))
    low_sample = random.sample(low, min(LOW_RISK_BUDGET, len(low)))

    combined = high_sample + medium_sample + low_sample
    random.shuffle(combined)
    return combined[:MAX_TRAINING_EXAMPLES]


def generate_training_data(
    profiles_path: Path,
    output_path: Path,
    teacher_dir: Path,
    force: bool = False,
) -> None:
    """Use the teacher model to generate (profile → narrative) training examples."""
    if output_path.exists() and not force:
        log(f"Training data already exists at {output_path}; skipping generation.")
        return

    if not profiles_path.exists():
        raise FileNotFoundError(
            f"Entity profiles not found: {profiles_path}. Run file2.py first."
        )

    log("Loading entity profiles...")
    all_profiles = read_jsonl(profiles_path)
    if not all_profiles:
        raise ValueError("No profiles found.")

    profiles = sample_profiles_for_training(all_profiles)
    log(f"Selected {len(profiles)} profiles for teacher generation.")

    log(f"Loading teacher model from {teacher_dir} ...")
    tokenizer = AutoTokenizer.from_pretrained(teacher_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        teacher_dir,
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    examples: list[dict[str, Any]] = []
    batch_prompts: list[list[dict[str, str]]] = []
    batch_profiles: list[dict[str, Any]] = []

    def flush_batch() -> None:
        nonlocal batch_prompts, batch_profiles, examples
        if not batch_prompts:
            return

        texts = [
            tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            for msgs in batch_prompts
        ]
        inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=2048)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        for i, profile in enumerate(batch_profiles):
            generated_tokens = outputs[i][inputs["input_ids"].shape[1] :]
            narrative = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            narrative = clean_teacher_output(narrative)
            if len(narrative.split()) >= 10:
                examples.append(
                    {
                        "entity_id": profile["entity_id"],
                        "profile_text": profile_to_text(profile),
                        "narrative": narrative,
                    }
                )

        batch_prompts = []
        batch_profiles = []

    log("Generating narratives with teacher model...")
    for profile in tqdm(profiles, desc="Teacher generation"):
        profile_text = profile_to_text(profile)
        msgs = build_teacher_prompt(profile_text)
        batch_prompts.append(msgs)
        batch_profiles.append(profile)
        if len(batch_prompts) >= TEACHER_BATCH_SIZE:
            flush_batch()
    flush_batch()

    if not examples:
        raise RuntimeError("Teacher model produced no valid training examples.")

    log(f"Generated {len(examples)} training examples.")
    write_jsonl(output_path, examples)


# ---------------------------------------------------------------------------
# SLM fine-tuning with Unsloth
# ---------------------------------------------------------------------------


def format_chat_example(example: dict[str, Any]) -> str:
    """Format a training example into SmolLM2 ChatML text."""
    messages = [
        {"role": "user", "content": f"Entity profile:\n{example['profile_text']}\n\nAudit narrative:"},
        {"role": "assistant", "content": example["narrative"]},
    ]
    # SmolLM2 tokenizer should be loaded by Unsloth; build a minimal ChatML string.
    return (
        "<|im_start|>user\n"
        f"{messages[0]['content']}<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{messages[1]['content']}<|im_end|>"
    )


def train_and_export_slm(
    training_data_path: Path,
    student_dir: Path,
    output_dir: Path,
    gguf_dir: Path,
    force: bool = False,
) -> Path:
    """Fine-tune SmolLM2-135M with LoRA using Unsloth and export a GGUF."""
    final_dir = output_dir / "final_model"
    gguf_dir.mkdir(parents=True, exist_ok=True)
    gguf_path = gguf_dir / "smollm135m_taxnet.gguf"

    if final_dir.exists() and gguf_path.exists() and not force:
        log(f"Model and GGUF already exist; skipping training.")
        return gguf_path

    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import load_dataset

    log(f"Loading student model from {student_dir} ...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(student_dir),
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
        use_rslora=False,
    )

    log("Loading training dataset...")
    dataset = load_dataset("json", data_files=str(training_data_path), split="train")
    dataset = dataset.map(lambda examples: {"text": [format_chat_example(e) for e in examples]}, batched=True)

    log("Starting fine-tuning...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=PER_DEVICE_BATCH_SIZE,
            gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
            warmup_steps=WARMUP_STEPS,
            num_train_epochs=NUM_EPOCHS,
            learning_rate=LEARNING_RATE,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=42,
            output_dir=str(output_dir / "trainer_output"),
            report_to="none",
        ),
    )

    trainer_stats = trainer.train()
    log(f"Training complete. Final loss: {trainer_stats.training_loss:.4f}")

    log(f"Saving LoRA adapter to {final_dir} ...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    log(f"Exporting GGUF to {gguf_path} ...")
    try:
        model.save_pretrained_gguf(str(gguf_dir), tokenizer, quantization_method="q4_k_m")
        # Unsloth may name the file differently; find and rename if needed.
        produced = next(gguf_dir.glob("*.gguf"), None)
        if produced and produced.name != gguf_path.name:
            produced.replace(gguf_path)
    except Exception as exc:
        log(f"WARNING: GGUF export failed: {exc}. LoRA adapter is still saved at {final_dir}.")
        raise

    return gguf_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune SmolLM2-135M for tax audit narratives.")
    parser.add_argument("--teacher-model", type=str, default=TEACHER_MODEL, help="HF repo ID for teacher model")
    parser.add_argument("--student-model", type=str, default=STUDENT_MODEL, help="HF repo ID for student model")
    parser.add_argument("--force-download", action="store_true", help="Re-download models.")
    parser.add_argument("--force-generate", action="store_true", help="Regenerate training data.")
    parser.add_argument("--force-train", action="store_true", help="Retrain the SLM even if output exists.")
    parser.add_argument("--skip-generate", action="store_true", help="Use existing training data.")
    parser.add_argument("--skip-train", action="store_true", help="Only generate data; do not train.")
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    final_gguf = GGUF_OUTPUT_DIR / "smollm135m_taxnet.gguf"
    if final_gguf.exists() and not args.force_train:
        log(f"GGUF already exists at {final_gguf}. Use --force-train to regenerate.")
        return 0

    # ------------------------------------------------------------------
    # Stage 1: download models
    # ------------------------------------------------------------------
    if is_checkpoint_complete("file3_models") and not args.force_download:
        log("Models checkpoint found; skipping download.")
    else:
        log("Downloading models...")
        download_model(args.teacher_model, MODELS_DIR / "teacher", force=args.force_download)
        download_model(args.student_model, MODELS_DIR / "student", force=args.force_download)
        save_checkpoint("file3_models", {"teacher": args.teacher_model, "student": args.student_model})

    teacher_dir = MODELS_DIR / "teacher"
    student_dir = MODELS_DIR / "student"

    # ------------------------------------------------------------------
    # Stage 2: generate training data
    # ------------------------------------------------------------------
    if not args.skip_generate:
        generate_training_data(
            PROFILES_PATH,
            TRAINING_DATA_PATH,
            teacher_dir,
            force=args.force_generate,
        )
        save_checkpoint("file3_generated", {"examples": TRAINING_DATA_PATH.stat().st_size})
    else:
        log("Skipping training data generation (--skip-generate).")
        if not TRAINING_DATA_PATH.exists():
            log(f"ERROR: {TRAINING_DATA_PATH} does not exist. Remove --skip-generate.")
            return 1

    if args.skip_train:
        log("Skipping training (--skip-train). Done.")
        return 0

    # ------------------------------------------------------------------
    # Stage 3: fine-tune SLM and export GGUF
    # ------------------------------------------------------------------
    if not args.skip_train:
        train_and_export_slm(
            TRAINING_DATA_PATH,
            student_dir,
            LORA_OUTPUT_DIR,
            GGUF_OUTPUT_DIR,
            force=args.force_train,
        )
        save_checkpoint("file3_trained", {"lora_dir": str(LORA_OUTPUT_DIR / "final_model"), "gguf": str(final_gguf)})
    else:
        log("Skipping training (--skip-train).")

    log("Done.")
    log(f"Artifacts: {TRAINING_DATA_PATH}, {LORA_OUTPUT_DIR / 'final_model'}, {GGUF_OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
