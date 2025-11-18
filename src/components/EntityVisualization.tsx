/**
 * Entity Visualization Component
 *
 * Shows extracted entities grouped by type and relationships between them
 */
import { Entity, Relationship } from "@/types/cognitivenexus";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { User, Briefcase, Building, Calendar, ArrowRight } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

interface EntityVisualizationProps {
  entities: Entity[];
  relationships: Relationship[];
}

export const EntityVisualization = ({
  entities,
  relationships,
}: EntityVisualizationProps) => {
  const getEntityIcon = (type: string) => {
    switch (type) {
      case "PERSON":
        return <User className="h-4 w-4" />;
      case "PROJECT":
        return <Briefcase className="h-4 w-4" />;
      case "TEAM":
        return <Building className="h-4 w-4" />;
      case "DATE":
        return <Calendar className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const getEntityColor = (type: string): string => {
    switch (type) {
      case "PERSON":
        return "bg-blue-100 text-blue-800 border-blue-300";
      case "PROJECT":
        return "bg-purple-100 text-purple-800 border-purple-300";
      case "TEAM":
        return "bg-green-100 text-green-800 border-green-300";
      case "DATE":
        return "bg-orange-100 text-orange-800 border-orange-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getPredicateLabel = (predicate: string): string => {
    switch (predicate) {
      case "WORKS_ON":
        return "works on";
      case "COMMUNICATES_WITH":
        return "communicates with";
      case "HAS_DEADLINE":
        return "has deadline";
      case "MENTIONED_WITH":
        return "mentioned with";
      default:
        return predicate.toLowerCase().replace(/_/g, " ");
    }
  };

  // Group entities by type
  const groupedEntities: Record<string, Entity[]> = entities.reduce((acc, entity) => {
    if (!acc[entity.type]) {
      acc[entity.type] = [];
    }
    acc[entity.type].push(entity);
    return acc;
  }, {} as Record<string, Entity[]>);

  const entityTypes = ["PERSON", "PROJECT", "TEAM", "DATE"];

  // Format team metadata for display
  const formatTeamMetadata = (metadata: any): string => {
    if (!metadata) return "";
    const parts = [];
    if (metadata.pillar) parts.push(metadata.pillar);
    if (metadata.team_name) parts.push(metadata.team_name);
    if (metadata.role) parts.push(metadata.role);
    return parts.join(" / ");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <span>Extracted Entities & Relationships</span>
          <Badge variant="outline" className="ml-auto">
            {entities.length} entities
          </Badge>
          <Badge variant="outline">
            {relationships.length} relationships
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="entities" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="entities">Entities</TabsTrigger>
            <TabsTrigger value="relationships">Relationships</TabsTrigger>
          </TabsList>

          <TabsContent value="entities" className="space-y-4 mt-4">
            {entityTypes.map((type) => {
              const typeEntities = groupedEntities[type] || [];
              if (typeEntities.length === 0) return null;

              return (
                <div key={type} className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                    {getEntityIcon(type)}
                    <span>{type.charAt(0) + type.slice(1).toLowerCase()}s</span>
                    <Badge variant="secondary" className="ml-auto">
                      {typeEntities.length}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2 pl-6">
                    {typeEntities.map((entity) => (
                      <div key={entity.id} className="flex flex-col gap-0.5">
                        <Badge
                          variant="outline"
                          className={`${getEntityColor(entity.type)} px-3 py-1`}
                        >
                          {entity.name}
                          {entity.confidence < 1.0 && (
                            <span className="ml-1 text-xs opacity-70">
                              ({(entity.confidence * 100).toFixed(0)}%)
                            </span>
                          )}
                        </Badge>
                        {entity.type === "TEAM" && entity.metadata && (
                          <span className="text-xs text-muted-foreground pl-1">
                            {formatTeamMetadata(entity.metadata)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {entities.length === 0 && (
              <div className="text-center text-sm text-muted-foreground py-8">
                No entities extracted
              </div>
            )}
          </TabsContent>

          <TabsContent value="relationships" className="space-y-3 mt-4">
            {relationships.length > 0 ? (
              relationships.map((rel, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 p-2 rounded-lg border bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-300">
                    {rel.subject}
                  </Badge>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <ArrowRight className="h-3 w-3" />
                    <span className="font-medium">{getPredicateLabel(rel.predicate)}</span>
                    <ArrowRight className="h-3 w-3" />
                  </div>
                  <Badge variant="outline" className="bg-purple-100 text-purple-800 border-purple-300">
                    {rel.object}
                  </Badge>
                  {rel.confidence < 1.0 && (
                    <Badge variant="secondary" className="ml-auto text-xs">
                      {(rel.confidence * 100).toFixed(0)}%
                    </Badge>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center text-sm text-muted-foreground py-8">
                No relationships inferred
              </div>
            )}
          </TabsContent>
        </Tabs>

        <div className="pt-4 border-t mt-4">
          <div className="text-xs text-muted-foreground">
            <strong>Smart Extraction:</strong> Agents extract hierarchical team data (pillars, teams, roles) and use context complexity to choose between fast and detailed extraction strategies.
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
