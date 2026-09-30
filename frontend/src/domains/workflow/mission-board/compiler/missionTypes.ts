import type {
  MissionGraphEntity,
  MissionGraphRelationship,
} from "@/domains/workflow/mission-board/graph/graphTypes";

export type MissionModel = {
  id: string;
  name: string;
  description: string;
  entities: MissionGraphEntity[];
  relationships: MissionGraphRelationship[];
};
