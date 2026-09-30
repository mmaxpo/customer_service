export default function AppContainer({ children }: { children: React.ReactNode }) {
    return <div className="mx-auto w-full max-w-7xl space-y-6">{children}</div>;
}