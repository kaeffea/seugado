// Shared placeholder page: every sidebar entry lands here until the real page
// for it is built, one slice at a time. No data fetching of any kind.
export default function EmConstrucao({ titulo }: { titulo: string }) {
  return (
    <section>
      <h1>{titulo}</h1>
      <p>Em construção.</p>
      <p>Esta página ainda não foi desenvolvida.</p>
    </section>
  );
}
