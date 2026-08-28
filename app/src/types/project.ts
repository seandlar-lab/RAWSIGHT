export type MetadataOrigin =
    | "embedded"
    | "attached"
    | "user"
    | "rawsight"
    | "ai";

export type MetadataScope =
    | "dataset"
    | "column"
    | "mixed";

export type MetadataLinkStatus =
    | "linked"
    | "suggested"
    | "unlinked";

export type MetadataLink = {
    id: string;

    metadataSourceId: string;

    targetType: "dataset" | "column";

    /**
     * Required when targetType = "column".
     */
    columnName?: string;

    /**
     * Example:
     * "Section: Grey seal"
     * "Page 42"
     * "Sheet: Data dictionary"
     */
    sourceReference?: string;

    status: MetadataLinkStatus;

    /**
     * Who or what established/suggested the link.
     */
    origin: MetadataOrigin;

    /**
     * Used mainly for RAWSIGHT/AI suggestions.
     * Human-confirmed links do not need a confidence score.
     */
    confidence?: number;
};

export type AnalysisStatus =
    | "not_run"
    | "running"
    | "completed"
    | "failed"
    | "stale";

export type DatasetKind = "source" | "derived";

export type DatasetOperationType =
    | "join"
    | "append"
    | "transform";

export type MetadataSourceType =
    | "embedded"
    | "file"
    | "user";

export type MetadataSource = {
    id: string;
    type: MetadataSourceType;

    name: string;
    path?: string;

    /**
     * Describes whether this source primarily applies
     * to the whole dataset, individual columns, or both.
     */
    scope: MetadataScope;

    addedAt: string;
};

export type SpecialValueDefinition = {
    value: string;

    meaning: string;

    /**
     * Example:
     * false → 0 means "no occurrence"
     * true  → -999 means "missing"
     */
    representsMissing: boolean;

    origin: MetadataOrigin;
};

export type ColumnMetadata = {
    columnName: string;

    description?: string;

    semanticType?: string;
    unit?: string;
    format?: string;

    specialValues: SpecialValueDefinition[];

    origin?: MetadataOrigin;
};

export type DatasetMetadata = {
    title?: string;
    description?: string;
    purpose?: string;

    temporalCoverage?: string;
    geographicalCoverage?: string;

    lineage?: string;
    limitations?: string;

    sources: MetadataSource[];

    links: MetadataLink[];

    columns: ColumnMetadata[];
};

export type SourceFile = {
    path: string;
    name: string;

    size: number;

    /**
     * Used to detect if the original source
     * has changed since it was added.
     */
    fingerprint?: string;
};

export type DerivedDatasetOperation = {
    type: DatasetOperationType;

    /**
     * IDs of datasets used to create this dataset.
     */
    parentDatasetIds: string[];

    description?: string;
};

export type DataExpectation = {
    id: string;

    columnName?: string;

    rule:
    | "unique"
    | "not_null"
    | "allowed_values"
    | "type"
    | "range"
    | "custom";

    description: string;

    enabled: boolean;

    origin: MetadataOrigin;
};

export type DatasetAnalysisState = {
    light: {
        status: AnalysisStatus;
        lastRunAt?: string;
    };

    deep: {
        status: AnalysisStatus;
        lastRunAt?: string;
    };
};

export type DatasetStructureColumn = {
    name: string;
    technicalType: string;
};

export type DatasetStructure = {
    columnCount: number;
    columns: DatasetStructureColumn[];
    inspectedAt: string;
};

export type RawsightDataset = {
    id: string;

    name: string;

    kind: DatasetKind;

    /**
     * Present for original source datasets.
     */
    source?: SourceFile;

    /**
     * Present for datasets created inside RAWSIGHT.
     */
    derivedFrom?: DerivedDatasetOperation;

    structure?: DatasetStructure;

    metadata: DatasetMetadata;

    expectations: DataExpectation[];

    analysis: DatasetAnalysisState;

    createdAt: string;
    updatedAt: string;
};

export type RawsightProject = {
    schemaVersion: 1;

    id: string;
    name: string;

    createdAt: string;
    updatedAt: string;

    /**
     * A project can contain any number of
     * source and derived datasets.
     */
    datasets: RawsightDataset[];

    /**
     * Dataset currently selected in the UI.
     */
    activeDatasetId?: string;
};