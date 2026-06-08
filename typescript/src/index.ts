// Auto-generated from heritage-types TypeSpec source.
// Do not edit directly — edit spec/main.tsp and run `npm run build`.

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
  findIds?: uuid[];
  sampleIds?: uuid[];
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
