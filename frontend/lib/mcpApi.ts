/**
 * MCP API Integration for ArchAI Frontend
 * Provides AI-powered design assistance through Model Context Protocol
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AIAnalysisRequest {
  project_id: string;
  analysis_type?: "comprehensive" | "layout" | "compliance" | "cost";
}

export interface AIOptimizationRequest {
  project_id: string;
  optimization_goals: string[];
  current_layout?: any;
}

export interface AISuggestion {
  id: string;
  type: string;
  title: string;
  description: string;
  impact: string;
  priority: "high" | "medium" | "low";
  action: string;
  parameters: Record<string, any>;
}

export interface AIAnalysisResponse {
  project_id: string;
  analysis_type: string;
  analysis: {
    metrics: {
      space_efficiency: number;
      natural_light_score: number;
      ventilation_score: number;
      privacy_score: number;
    };
    insights: Array<{
      type: string;
      severity: string;
      message: string;
      suggestion: string;
    }>;
    room_analysis: {
      total_rooms: number;
      has_essential_rooms: boolean;
      built_area: number;
    };
  };
  timestamp: string;
}

export interface AIOptimizationResponse {
  project_id: string;
  optimization_goals: string[];
  suggestions: Array<{
    id: string;
    title: string;
    description: string;
    impact: string;
    type: string;
    priority: string;
    changes: Array<{
      room?: string;
      element?: string;
      action: string;
      [key: string]: any;
    }>;
  }>;
  timestamp: string;
}

class MCPApi {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE}/api/mcp${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`MCP API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Analyze project using AI and get insights
   */
  async analyzeProject(request: AIAnalysisRequest): Promise<AIAnalysisResponse> {
    return this.request<AIAnalysisResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Generate AI-powered design optimizations
   */
  async optimizeDesign(request: AIOptimizationRequest): Promise<AIOptimizationResponse> {
    return this.request<AIOptimizationResponse>("/optimize", {
      method: "POST", 
      body: JSON.stringify(request),
    });
  }

  /**
   * Get AI-powered design suggestions
   */
  async getSuggestions(request: AIAnalysisRequest): Promise<{
    suggestions: AISuggestion[];
    analysis: any;
    timestamp: string;
  }> {
    return this.request("/suggest", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Validate building compliance using AI
   */
  async validateCompliance(projectId: string): Promise<{
    project_id: string;
    compliance_status: string;
    checks: Record<string, any>;
    issues: Array<{
      type: string;
      severity: string;
      message: string;
      solution: string;
    }>;
    recommendations: string[];
  }> {
    return this.request("/validate-compliance", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    });
  }

  /**
   * Get AI-powered cost estimation
   */
  async estimateCosts(projectId: string): Promise<{
    project_id: string;
    total_cost: number;
    cost_per_sqft: number;
    breakdown: Record<string, { amount: number; percentage: number }>;
    market_factors: Record<string, any>;
    optimization_opportunities: Array<{
      area: string;
      potential_savings: number;
      description: string;
    }>;
  }> {
    return this.request("/estimate-costs", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    });
  }

  /**
   * Simulate AI chat conversation
   */
  async chatWithAI(projectId: string, message: string): Promise<{
    response: string;
    suggestions?: string[];
    data?: any;
  }> {
    // Simulate AI chat responses based on message content
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes("analyze") || lowerMessage.includes("design")) {
      const analysis = await this.analyzeProject({ project_id: projectId });
      return {
        response: `I've analyzed your design. Space efficiency is ${analysis.analysis.metrics.space_efficiency}%, natural light score is ${analysis.analysis.metrics.natural_light_score}%. ${analysis.analysis.insights.length > 0 ? 'I found some optimization opportunities.' : 'Your design looks good!'}`,
        suggestions: ["Show optimization suggestions", "Get detailed analysis", "Check compliance"],
        data: analysis
      };
    }
    
    if (lowerMessage.includes("optimize") || lowerMessage.includes("improve")) {
      return {
        response: "I can help optimize your design for better space utilization, natural light, ventilation, or cost efficiency. What would you like to focus on?",
        suggestions: ["Maximize natural light", "Improve ventilation", "Optimize space efficiency", "Reduce costs"]
      };
    }
    
    if (lowerMessage.includes("compliance") || lowerMessage.includes("code")) {
      const compliance = await this.validateCompliance(projectId);
      return {
        response: `Compliance check complete. Status: ${compliance.compliance_status}. ${compliance.issues.length > 0 ? `Found ${compliance.issues.length} issues that need attention.` : 'All checks passed!'}`,
        suggestions: ["View detailed report", "Fix issues", "Get recommendations"],
        data: compliance
      };
    }
    
    if (lowerMessage.includes("cost") || lowerMessage.includes("estimate")) {
      const costs = await this.estimateCosts(projectId);
      return {
        response: `Cost estimation complete. Total project cost: ₹${(costs.total_cost / 100000).toFixed(1)}L at ₹${costs.cost_per_sqft}/sq.ft. I found ${costs.optimization_opportunities.length} cost optimization opportunities.`,
        suggestions: ["View cost breakdown", "See optimization opportunities", "Compare alternatives"],
        data: costs
      };
    }
    
    // Default response
    return {
      response: "I'm your AI architectural assistant. I can help you analyze your design, optimize layouts, check compliance, estimate costs, and provide design suggestions. What would you like to work on?",
      suggestions: ["Analyze my design", "Optimize layout", "Check compliance", "Estimate costs"]
    };
  }
}

export const mcpApi = new MCPApi();