import { Phase2ManualDemo } from "../components/Phase2/Phase2ManualDemo"

interface Phase2ManualDemoPageProps {
  onCompleted?: () => void
}

export default function Phase2ManualDemoPage({ onCompleted }: Phase2ManualDemoPageProps) {
  return <Phase2ManualDemo onCompleted={onCompleted} />
}
