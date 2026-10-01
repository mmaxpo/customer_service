type Props = {
    title?: string;
    description?: string;
    children: React.ReactNode;
    action?: React.ReactNode;
};

export default function SectionCard({ title, description, children, action }: Props) {
    return (
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
            {(title || description || action) && (
                <div className="mb-5 flex items-start justify-between gap-4">
                    <div>
                        {title && <h2 className="font-semibold text-foreground">{title}</h2>}
                        {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
                    </div>
                    {action}
                </div>
            )}
            {children}
        </section>
    );
}