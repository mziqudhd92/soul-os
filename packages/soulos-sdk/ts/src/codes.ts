/** Stable RFC 7807 Problem Details ``code`` values for hybrid turn contracts. */
export const TURN_CONTRACT_VIOLATION = "TURN_CONTRACT_VIOLATION";
export const TURN_REJECT_TOKEN = "TURN_REJECT_TOKEN";
export const TURN_STEP_MISMATCH = "TURN_STEP_MISMATCH";
export const TURN_STATE_STALE = "TURN_STATE_STALE";
export const TURN_SESSION_EXPIRED = "TURN_SESSION_EXPIRED";

export const TURN_ERROR_CODES = [
  TURN_CONTRACT_VIOLATION,
  TURN_REJECT_TOKEN,
  TURN_STEP_MISMATCH,
  TURN_STATE_STALE,
  TURN_SESSION_EXPIRED,
] as const;

export type TurnErrorCode = (typeof TURN_ERROR_CODES)[number];
