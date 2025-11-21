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
}

export interface SimulationRequest {
    concept: ConceptInput;
    persona_group?: string;
    questions?: string[];
    population_spec?: any; // Using any for now to avoid full typing of complex nested structures
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
    };
    distribution: {
        mean: number;
        top2box: number;
        sample_n: number;
    };
    rationales: string[];
    themes: string[];
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
}

export const runSimulation = async (request: SimulationRequest): Promise<SimulationResponse> => {
    const response = await axios.post<SimulationResponse>(`${API_URL}/simulate`, request);
    return response.data;
};
