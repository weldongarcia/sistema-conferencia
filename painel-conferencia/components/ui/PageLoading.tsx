type PageLoadingProps = {
  mensagem: string;
};

export default function PageLoading({ mensagem }: PageLoadingProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas text-ink">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-line border-t-brand-light" />

        <p className="text-sm text-muted">{mensagem}</p>
      </div>
    </main>
  );
}
