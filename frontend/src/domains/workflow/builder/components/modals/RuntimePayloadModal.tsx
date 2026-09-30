"use client";

type Props = {
    open: boolean;
    payload: any;
    onClose: () => void;
};

export default function RuntimePayloadModal({ open, payload, onClose }: Props) {
    if (!open) return null;

    const json = JSON.stringify(payload, null, 2);

    async function copy() {
        await navigator.clipboard.writeText(json);
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6">
            <div className="flex max-h-[88vh] w-full max-w-5xl flex-col rounded-3xl bg-white shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                    <div>
                        <div className="font-semibold text-slate-950">Runtime Payload Preview</div>
                        <div className="text-xs text-slate-500">
                            Tool reference nodes are removed before backend execution.
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={copy}
                            className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold hover:bg-slate-50"
                        >
                            Copy JSON
                        </button>

                        <button
                            onClick={onClose}
                            className="rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                        >
                            Close
                        </button>
                    </div>
                </div>

                <pre className="overflow-auto p-5 text-xs leading-5 text-slate-800">
                    {json}
                </pre>
            </div>
        </div>
    );
}