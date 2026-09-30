type Props = {
    title?: string;
    description?: string;
    children: React.ReactNode;
    action?: React.ReactNode;
};

export default function SectionCard({ title, description, children, action }: Props) {
    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {(title || description || action) && (
                <div className="mb-5 flex items-start justify-between gap-4">
                    <div>
                        {title && <h2 className="font-semibold text-slate-950">{title}</h2>}
                        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
                    </div>
                    {action}
                </div>
            )}
            {children}
        </section>
    );
}