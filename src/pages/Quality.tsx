/**
 * Quality Dashboard Page - Phase 6 Stage 6
 * 
 * Full-page view of task quality metrics and trust index
 */

import { QualityDashboard } from "@/components/QualityDashboard";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Quality = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Header with navigation */}
      <div className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/")}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Board
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Quality Dashboard</h1>
              <p className="text-sm text-muted-foreground">
                Trust metrics and task quality analytics
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="container mx-auto px-4 py-8">
        <QualityDashboard />
      </div>
    </div>
  );
};

export default Quality;

