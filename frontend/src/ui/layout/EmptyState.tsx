type Props = {
    title: string;
    description?: string;
    icon?: React.ReactNode;
    action?: React.ReactNode;
};

export default function EmptyState({ title, description, icon, action }: Props) {
    return (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            {icon && <div className="mb-3 text-slate-500">{icon}</div>}
            <h3 className="font-semibold text-slate-950">{title}</h3>
            {description && <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">{description}</p>}
            {action && <div className="mt-5">{action}</div>}
        </div>
    );
}