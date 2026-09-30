export type MissionGraphEntityType =
  | "mission"
  | "agent"
  | "tool"
  | "variable"
  | "knowledge"
  | "decision"
  | "response";

export type MissionGraphEntity = {
  id: string;
  type: MissionGraphEntityType;
  label: string;
  description: string;
};

export type MissionGraphRelationship = {
  id: string;
  source: string;
  target: string;
  label: string;
};

export type MissionKnowledgeGraph = {
  entities: MissionGraphEntity[];
  relationships: MissionGraphRelationship[];
};
