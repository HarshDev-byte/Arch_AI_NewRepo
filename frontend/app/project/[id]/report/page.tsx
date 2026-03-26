export default function ReportPage({ params }: { params: { id: string } }) {
  return <div><h1>Cost & Compliance Report – {params.id}</h1></div>;
}
