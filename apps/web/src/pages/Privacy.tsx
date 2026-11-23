import { LegalLayout } from '@/components/layout/LegalLayout'

const SECTIONS = [
  {
    title: 'Data we collect',
    body:
      "Cloud billing, usage, inventory, configuration, and metric records from connected providers. User identifiers and session events required for authentication and audit. Chat messages sent to the AI Analyst.",
  },
  {
    title: 'How we use data',
    body:
      "To compute cost summaries, detect anomalies, produce recommendations, and provide the AI Analyst with grounded context. Cloud secrets are stored in the server-side secret manager and are never sent to the LLM.",
  },
  {
    title: 'Data retention',
    body:
      "Raw provider responses are retained for a configurable period. Audit events are retained for compliance. Customers may request deletion.",
  },
  {
    title: 'Sharing',
    body:
      "Data is not sold. Data is shared with the LLM provider only to the extent necessary to answer a user's question, following the documented context strategy in the architecture.",
  },
  {
    title: 'Security',
    body:
      "Least-privilege cloud roles by default, tenant isolation on every record, and audit logging for every privileged operation.",
  },
]

export function Privacy() {
  return (
    <LegalLayout
      title="Privacy Policy"
      intro="The sections below outline the topics that the final document should cover, based on the product's documented data handling."
      sections={SECTIONS}
      footer="This draft contains no legal commitments. It will be replaced when the final legal text is ready."
    />
  )
}