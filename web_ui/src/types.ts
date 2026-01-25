import type { SimulationRequest, SimulationResponse } from './api';

export type RunRecord = {
    id: string;
    label: string;
    createdAt: number;
    request: SimulationRequest;
    response: SimulationResponse;
};

export type QuestionAggregate = NonNullable<SimulationResponse['questions']>[number];
