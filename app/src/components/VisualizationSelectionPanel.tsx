import type { VisualizationRow } from "../types/visualization";


type VisualizationSelectionPanelProps = {
    selectedRowCount: number | null;
    selectedSourceRow: VisualizationRow | null;
};

export function VisualizationSelectionPanel({
    selectedRowCount,
    selectedSourceRow,
}: VisualizationSelectionPanelProps) {
    return (
        <>
            {selectedRowCount !== null && (
                <div
                    style={{
                        marginTop: "12px",
                        fontSize: "14px",
                    }}
                >
                    <strong>Selected rows</strong>
                    <div>{selectedRowCount} rows</div>
                </div>
            )}

            {selectedSourceRow && (
                <div
                    style={{
                        marginTop: "12px",
                        fontSize: "14px",
                    }}
                >
                    <strong>Source row</strong>

                    {Object.entries(selectedSourceRow).map(
                        ([columnName, value]) => (
                            <div key={columnName}>
                                {columnName}: {String(value)}
                            </div>
                        ),
                    )}
                </div>
            )}
        </>
    );
}