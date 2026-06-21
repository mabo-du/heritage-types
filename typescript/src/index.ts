// Auto-generated from heritage-types TypeSpec source.
// Do not edit directly — edit spec/main.tsp and run `npm run build`.
//
// Scalars and enums are hoisted to root-level declarations so every
// interface below resolves unambiguously. Custom format / pattern hints
// are preserved as `// comments`.


export type SchemaVer = string;  // pattern: ^\d+-\d+-\d+$
export type datetime = string;  // ISO 8601 datetime
export type fieldId = string;  // pattern: ^\[?[A-Za-z0-9]+\]?$
export type uuid = string;  // RFC 4122 UUID

export enum AgentType {
  Human = "Human",
  AIModel = "AIModel",
  Software = "Software",
}

export enum MaterialClass {
  Pottery = "Pottery",
  Bone = "Bone",
  Flint = "Flint",
  Metal = "Metal",
  CBM = "CBM",
  Glass = "Glass",
  Shell = "Shell",
  Slag = "Slag",
  Wood = "Wood",
  Textile = "Textile",
  Leather = "Leather",
  Environmental = "Environmental",
  Other = "Other",
}

export enum RelationshipType {
  Above = "Above",
  Below = "Below",
  Equals = "Equals",
  Contemporary = "Contemporary",
  Cuts = "Cuts",
  Fills = "Fills",
}

export enum SampleType {
  Radiocarbon = "Radiocarbon",
  Environmental = "Environmental",
  Isotopic = "Isotopic",
  Dendrochronology = "Dendrochronology",
  Archaeomagnetic = "Archaeomagnetic",
  OSL = "OSL",
  Other = "Other",
}

export enum UnitType {
  Deposit = "Deposit",
  Cut = "Cut",
  Interface = "Interface",
  Masonry = "Masonry",
  Natural = "Natural",
  Unknown = "Unknown",
}

export interface SiteMetadata {
  projectId: uuid;
  projectName: string;
  jurisdiction?: string;
  gridReference?: string;
  epsgCode?: number;
  director?: string;
  siteCode?: string;
  excavationYear?: string;
  createdAt?: datetime;
  updatedAt?: datetime;
}

export interface StratigraphicUnit {
  id: uuid;
  contextNumber: fieldId;
  unitType: UnitType;
  description?: string;
  interpretation?: string;
  period?: string;
  phase?: string;
  length_m?: number;
  width_m?: number;
  depth_m?: number;
  mediaPresent?: boolean;
  confidence?: number;
  findIds?: (uuid)[];
  sampleIds?: (uuid)[];
}

export interface StratigraphicRelationship {
  id: uuid;
  sourceId: uuid;
  targetId: uuid;
  relationshipType: RelationshipType;
  confidence?: number;
  notes?: string;
}

export interface Find {
  id: uuid;
  contextId: uuid;
  findNumber?: string;
  materialClass: MaterialClass;
  typology?: string;
  count?: number;
  weight_g?: number;
  period?: string;
  description?: string;
  recorded?: boolean;
}

export interface Sample {
  id: uuid;
  contextId: uuid;
  sampleId?: string;
  sampleType: SampleType;
  volume_l?: number;
  weight_g?: number;
  notes?: string;
}

export interface Chronology {
  id: uuid;
  sampleId?: uuid;
  contextId?: uuid;
  labCode?: string;
  uncalBp?: number;
  error?: number;
  calibrationCurve?: string;
  calibratedRange68?: string;
  calibratedRange95?: string;
  datingMethod?: string;
  datedMaterial?: string;
  delta13C?: number;
}

export interface DigitalAsset {
  id: uuid;
  contextId?: uuid;
  filePath: string;
  assetType: string;
  mimeType?: string;
  fileSizeBytes?: string;
  checksumSha256?: string;
  caption?: string;
  orientation?: string;
  scale?: string;
}

export interface ProvenanceAgent {
  id: uuid;
  agentType: AgentType;
  name: string;
  version?: string;
  modelId?: string;
}

export interface ProvenanceActivity {
  id: uuid;
  activityType: string;
  startedAtTime?: datetime;
  agent: ProvenanceAgent;
}

export interface ProvenanceRecord {
  entity: uuid;
  wasGeneratedBy?: ProvenanceActivity;
  wasAttributedTo?: ProvenanceAgent;
  generatedAtTime: datetime;
  confidence?: number;
  notes?: string;
}

export interface HeritageDataPackage {
  schemaVersion: SchemaVer;
  createdAt: datetime;
  updatedAt?: datetime;
  provenance?: string;
  provenanceLog?: (ProvenanceRecord)[];
  metadata?: SiteMetadata;
  contexts: (StratigraphicUnit)[];
  relationships: (StratigraphicRelationship)[];
  finds: (Find)[];
  samples: (Sample)[];
  dates: (Chronology)[];
  assets: (DigitalAsset)[];
}
