type Props = {
    eyebrow?: string;
    title: string;
    description?: string;
    actions?: React.ReactNode;
};

export default function PageHeader({ eyebrow, title, description, actions }: Props) {
    return (
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
                {eyebrow && <div className="text-sm font-medium text-text-secondary">{eyebrow}</div>}
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">{title}</h1>
                {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">{description}</p>}
            </div>
            {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
    );
}