export const RESEARCHER_ROLES = ['overview', 'retrieve', 'structure', 'compare', 'concept', 'validate'];

// Selection never starts work. Only the execution state (or the explicitly
// labelled, separate motion preview) chooses an animated researcher.
export function researcherPose(id, { activeIds = [], plannerWorking = false, reducedMotion = false, elapsed = 0 } = {}) {
  const working = id === 'overview' ? plannerWorking : activeIds.includes(id);
  return { working, frame: working && !reducedMotion ? Math.floor(Math.max(0, elapsed) * 2.2) % 2 : 0 };
}
