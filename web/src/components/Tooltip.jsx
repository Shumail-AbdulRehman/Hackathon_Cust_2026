import { useState } from 'react'

const DEFINITIONS = {
  'Deviation score': 'How much this entity’s income/assets differ from expected norms.',
  'Direct risk': 'Risk calculated from the entity’s own records, independent of associates.',
  'Associate proxy score': 'Risk inherited from linked entities such as family, shared addresses, or phone numbers.',
  'ML score': 'Machine-learning risk estimate; shown only when a pretrained model is loaded.',
  'Risk tier': 'Overall classification: green (low) → yellow → orange → red → critical.',
  'Entity resolution': 'The process of linking records that belong to the same person or organization.',
  'LLI ratio': 'Lifestyle-to-income ratio: spending and assets divided by declared income.',
  'Confidence': 'How much evidence the scoring model had for this profile.',
}

export default function Tooltip({ term, children }) {
  const [visible, setVisible] = useState(false)
  const text = DEFINITIONS[term]
  if (!text) return children

  return (
    <span
      className="tooltip-wrap"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      tabIndex={0}
      aria-describedby={`tip-${term}`}
    >
      {children}
      {visible && (
        <span id={`tip-${term}`} className="tooltip-popup" role="tooltip">
          {text}
        </span>
      )}
    </span>
  )
}
