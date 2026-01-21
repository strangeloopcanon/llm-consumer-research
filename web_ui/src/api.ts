import axios from 'axios';

const API_URL = 'http://localhost:8000';

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

export interface SimulationRequest {
    concept: ConceptInput;
    persona_group?: string;
    questionnaire?: QuestionSpec[];
    questions?: string[];
    population_spec?: unknown;
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
