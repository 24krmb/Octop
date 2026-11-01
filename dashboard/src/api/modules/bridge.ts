/**
 * Bridge module — stub after the 24K-Claw cloud-collab removal.
 * Kept so legacy imports compile; every call is a no-op.
 */
export const bridgeApi = {
  async list(): Promise<never[]> {
    return [];
  },
  async listAgents(): Promise<never[]> {
    return [];
  },
  async getSessions(): Promise<never[]> {
    return [];
  },
  async getBrowserSessions(_connId?: string): Promise<never[]> {
    return [];
  },
  async browserHandoff(): Promise<{ ok: boolean }> {
    return { ok: false };
  },
  async handoff(): Promise<{ ok: boolean }> {
    return { ok: false };
  },
  async create(): Promise<never> {
    throw new Error("bridge removed");
  },
  async patch(): Promise<never> {
    throw new Error("bridge removed");
  },
  async probe(): Promise<never> {
    throw new Error("bridge removed");
  },
  async remove(): Promise<void> {},
  async test(): Promise<never> {
    throw new Error("bridge removed");
  },
};
export default bridgeApi;
