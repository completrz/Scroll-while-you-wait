// Browser-only experiment assignment. No network, no personal identifiers.
// Consent and activation are stored locally; assignments use crypto randomness.
const EXPERIMENT_DEFAULTS = { researchExperimentEnabled: false, researchExperimentConsent: false };
async function experimentSettings(){
  return chrome.storage.local.get(EXPERIMENT_DEFAULTS);
}
async function assignExperiment(tabId, isNewResponse){
  const settings = await experimentSettings();
  if(!settings.researchExperimentEnabled || !settings.researchExperimentConsent)
    return {condition:'observational',allowPlayback:true};
  const key='experimentTabAssignments';
  const data=await chrome.storage.session.get(key);
  const assignments=data[key]||{};
  if(!isNewResponse && assignments[tabId]) return assignments[tabId];
  const bytes=new Uint8Array(1);crypto.getRandomValues(bytes);
  const treatment=(bytes[0]%2)===0;
  assignments[tabId]={condition:treatment?'treatment':'control',allowPlayback:treatment,
    assignedAt:Date.now()};
  await chrome.storage.session.set({[key]:assignments});
  return assignments[tabId];
}
async function clearExperiment(tabId){
 const key='experimentTabAssignments';
 const data=await chrome.storage.session.get(key);
 const a=data[key]||{};
 delete a[tabId];
 await chrome.storage.session.set({[key]:a});
}
