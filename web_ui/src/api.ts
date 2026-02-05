import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface ConceptInput {
    title?: string;
    text?: string;
    price?: string;
    url?: string;
}

export interface SimulationOptions {
    n: number;
    total_n?: number;
    stratified: boolean;
    providers: string[];
    temperature?: number;
    additional_instructions?: string;
    seed?: number;
    include_respondents?: boolean;
}

export interface QuestionSpec {
    id?: string;
    text: string;
    intent?: string;
    anchor_bank?: string;
}

export interface PanelContextSpec {
    text?: string;
    chunks?: string[];
    mode?: 'shared' | 'round_robin' | 'sample';
    chunks_per_persona?: number;
}

export type PopulationSpecPayload = Record<string, unknown>;

export interface SimulationRequest {
    concept: ConceptInput;
    persona_group?: string;
    questionnaire?: QuestionSpec[];
    questions?: string[];
    population_spec?: PopulationSpecPayload;
    panel_context?: PanelContextSpec;
    options: SimulationOptions;
}

export interface PersonaResult {
    persona: {
        name: string;
        weight: number;
        age?: string;
        region?: string;
        income?: string;
        descriptors?: string[];
        context?: string[];
    };
    distribution: {
        mean: number;
        top2box: number;
        sample_n: number;
    };
    rationales: string[];
    themes: string[];
    question_results?: Array<{
        question_id: string;
        question: string;
        intent: string;
        anchor_bank: string;
        distribution: {
            mean: number;
            top2box: number;
            sample_n: number;
            ratings: number[];
            pmf: number[];
        };
        rationales: string[];
        themes: string[];
    }>;
    respondents?: Array<{
        respondent_id: string;
        answers: Array<{
            question_id: string;
            intent: string;
            anchor_bank: string;
            provider: string;
            model: string;
            rationale: string;
            score_mean: number;
        }>;
    }>;
}

export interface SimulationResponse {
    aggregate: {
        mean: number;
        top2box: number;
        sample_n: number;
        ratings: number[];
        pmf: number[];
    };
    personas: PersonaResult[];
    metadata: Record<string, string>;
    questions?: Array<{
        question_id: string;
        question: string;
        intent: string;
        anchor_bank: string;
        aggregate: {
            mean: number;
            top2box: number;
            sample_n: number;
            ratings: number[];
            pmf: number[];
        };
    }>;
}

export const runSimulation = async (request: SimulationRequest): Promise<SimulationResponse> => {
    const response = await axios.post<SimulationResponse>(`${API_URL}/simulate`, request);
    return response.data;
};

export interface PanelPreviewResponse {
    panel: Array<{
        persona: PersonaResult['persona'] & { weight: number };
        draws: number;
    }>;
    questions: QuestionSpec[];
    metadata: Record<string, string>;
}

export const previewPanel = async (request: SimulationRequest): Promise<PanelPreviewResponse> => {
    const response = await axios.post<PanelPreviewResponse>(`${API_URL}/panel-preview`, request);
    return response.data;
};

export interface PersonaGroupSummary {
    name: string;
    description: string;
    persona_count: number;
    source?: string;
}

export const listPersonaGroups = async (): Promise<PersonaGroupSummary[]> => {
    const response = await axios.get<PersonaGroupSummary[]>(`${API_URL}/persona-groups`);
    return response.data;
};

// ============================================================================
// Run History API
// ============================================================================

export interface RunSummary {
    id: string;
    created_at: string;
    label: string | null;
    status: string;
}

export interface RunDetail extends RunSummary {
    request: SimulationRequest;
    response: SimulationResponse;
}

export const listRuns = async (limit = 50, offset = 0): Promise<RunSummary[]> => {
    const response = await axios.get<RunSummary[]>(`${API_URL}/runs`, {
        params: { limit, offset },
    });
    return response.data;
};

export const getRunById = async (runId: string): Promise<RunDetail> => {
    const response = await axios.get<RunDetail>(`${API_URL}/runs/${runId}`);
    return response.data;
};

export const deleteRunById = async (runId: string): Promise<void> => {
    await axios.delete(`${API_URL}/runs/${runId}`);
};

// ============================================================================
// Audience Builder API
// ============================================================================

export interface AudienceBuildResponse {
    population_spec: PopulationSpecPayload;
    reasoning: string;
    evidence_summary_length: number;
}

export const buildAudience = async (
    files: File[],
    targetDescription?: string
): Promise<AudienceBuildResponse> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (targetDescription) {
        formData.append('target_description', targetDescription);
    }
    const response = await axios.post<AudienceBuildResponse>(
        `${API_URL}/audience/build`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
};
