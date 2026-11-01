/**
 * Browser module — removed in the 24K-Claw slim-down.
 * Kept as a stub so legacy imports compile; every call is a no-op.
 */
export const browserApi = {
  async startRecording(): Promise<{ ok: boolean; recording?: unknown }> {
    return { ok: false };
  },
  async stopRecording(): Promise<{ ok: boolean }> {
    return { ok: false };
  },
  async getSessions(): Promise<never[]> {
    return [];
  },
  async handoff(): Promise<{ ok: boolean }> {
    return { ok: false };
  },
  async stopAndGenerateSkill(payload?: Record<string, unknown>): Promise<{
    ok: boolean;
    recordingId?: string;
    skillContent?: string;
    skillName?: string;
    steps?: unknown[];
  }> {
    return { ok: false };
  },
  async recordReplayStatus(): Promise<{
    active?: { recordingId?: string } | null;
    latestRecordingId?: string;
  }> {
    return {};
  },
  async checkEnvStatus(_agentId?: string): Promise<{ ready: boolean; browsers_ok?: boolean }> {
    return { ready: false };
  },
  async listAgents(): Promise<never[]> {
    return [];
  },
};
export default browserApi;
