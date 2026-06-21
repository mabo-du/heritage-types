/**
 * heritage-types — Canonical Heritage Science Data Models
 *
 * License: MIT
 */

import "@typespec/json-schema";

using TypeSpec.JsonSchema;

// ── Scalars ──────────────────────────────────────────────────────────────────

@format("date-time")
scalar datetime extends string;

@format("uuid")
@pattern("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
scalar uuid extends string;

@pattern("^\\[?[A-Za-z0-9]+\\]?$")
scalar fieldId extends string;

// ── Enums ────────────────────────────────────────────────────────────────────

enum UnitType {
    Deposit,
    Cut,
    Interface,
    Masonry,
    Natural,
    Unknown,
}

enum RelationshipType {
    Above,
    Below,
    Equals,
    Contemporary,
    Cuts,
    Fills,
}

enum MaterialClass {
    Pottery,
    Bone,
    Flint,
    Metal,
    CBM,
    Glass,
    Shell,
    Slag,
    Wood,
    Textile,
    Leather,
    Environmental,
    Other,
}

enum SampleType {
    Radiocarbon,
    Environmental,
    Isotopic,
    Dendrochronology,
    Archaeomagnetic,
    OSL,
    Other,
}

// ── Core Models ──────────────────────────────────────────────────────────────

@jsonSchema
model SiteMetadata {
    projectId: uuid;
    projectName: string;
    jurisdiction?: string;
    gridReference?: string;
    epsgCode?: int32;
    director?: string;
    siteCode?: string;
    excavationYear?: string;
    createdAt?: datetime;
    updatedAt?: datetime;
}

@jsonSchema
model StratigraphicUnit {
    id: uuid;
    contextNumber: fieldId;
    unitType: UnitType;
    description?: string;
    interpretation?: string;
    period?: string;
    phase?: string;
    length_m?: float32;
    width_m?: float32;
    depth_m?: float32;
    mediaPresent?: boolean;
    confidence?: float32;
    findIds?: uuid[];
    sampleIds?: uuid[];
}

@jsonSchema
model StratigraphicRelationship {
    id: uuid;
    sourceId: uuid;
    targetId: uuid;
    relationshipType: RelationshipType;
    confidence?: float32;
    notes?: string;
}

@jsonSchema
model Find {
    id: uuid;
    contextId: uuid;
    findNumber?: string;
    materialClass: MaterialClass;
    typology?: string;
    count?: int32;
    weight_g?: float32;
    period?: string;
    description?: string;
    recorded?: boolean;
}

@jsonSchema
model Sample {
    id: uuid;
    contextId: uuid;
    sampleId?: string;
    sampleType: SampleType;
    volume_l?: float32;
    weight_g?: float32;
    notes?: string;
}

@jsonSchema
model Chronology {
    id: uuid;
    sampleId?: uuid;
    contextId?: uuid;
    labCode?: string;
    uncalBp?: int32;
    error?: int32;
    calibrationCurve?: string;
    calibratedRange68?: string;
    calibratedRange95?: string;
    datingMethod?: string;
    datedMaterial?: string;
    delta13C?: float32;
}

@jsonSchema
model DigitalAsset {
    id: uuid;
    contextId?: uuid;
    filePath: string;
    assetType: string;
    mimeType?: string;
    fileSizeBytes?: int64;
    checksumSha256?: string;
    caption?: string;
    orientation?: string;
    scale?: string;
}

// ── SchemaVer scalar ─────────────────────────────────────────────────────────
// Format: MODEL-REVISION-ADDITION (e.g. "1-0-0")
// MODEL increments on breaking changes, REVISION on non-breaking additions,
// ADDITION on purely additive changes (new optional fields only).

@pattern("^\\d+-\\d+-\\d+$")
scalar SchemaVer extends string;

// ── Agent types (W3C PROV-O inspired) ────────────────────────────────────────

enum AgentType {
    Human,
    AIModel,
    Software,
}

@jsonSchema
model ProvenanceAgent {
    id: uuid;
    agentType: AgentType;
    name: string;           // e.g. "Mark Bouck" or "paleo-id-v1"
    version?: string;       // software version
    modelId?: string;       // for AI agents: model identifier
}

@jsonSchema
model ProvenanceActivity {
    id: uuid;
    activityType: string;   // e.g. "SpeciesIdentification", "AgeModelling"
    startedAtTime?: datetime;
    agent: ProvenanceAgent;
}

@jsonSchema
model ProvenanceRecord {
    entity: uuid;                       // ID of the record being described
    wasGeneratedBy?: ProvenanceActivity;
    wasAttributedTo?: ProvenanceAgent;
    generatedAtTime: datetime;
    @minValue(0.0)
    @maxValue(1.0)
    confidence?: float32;               // 0.0–1.0, for AI-generated assertions
    notes?: string;
}

@jsonSchema
model HeritageDataPackage {
    schemaVersion: SchemaVer;           // REQUIRED — e.g. "1-0-0"
    createdAt: datetime;
    updatedAt?: datetime;
    provenance?: string;                // legacy string provenance note
    provenanceLog?: ProvenanceRecord[]; // append-only assertion log
    metadata?: SiteMetadata;
    contexts: StratigraphicUnit[];
    relationships: StratigraphicRelationship[];
    finds: Find[];
    samples: Sample[];
    dates: Chronology[];
    assets: DigitalAsset[];
}
