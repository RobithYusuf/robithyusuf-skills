import {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender} from 'remotion';

// draft = fast preview: no motion blur, no grain, no depth blur. Wrap the composition in
// <DraftCtx.Provider value={draft}> and pass {"draft": true} as input props for stills and timing checks.
export const DraftCtx = createContext(false);
export const useDraft = () => useContext(DraftCtx);

// Every weight and style the video uses, in CSS font shorthand. Import the matching @fontsource files once
// (e.g. import '@fontsource/inter/latin-800.css') in this module or in Root.
export const FONT_PROBES = ['400 40px "Inter"', '600 40px "Inter"', '800 40px "Inter"', 'italic 800 40px "Inter"'];

// @fontsource registers @font-face lazily, so without this gate the first frames render with the fallback font and
// text widths jump. Call once at the top of the composition component.
export const useFontGate = (probes: string[] = FONT_PROBES) => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all(probes.map((p) => document.fonts.load(p)))
      .then(() => document.fonts.ready)
      .finally(() => continueRender(handle));
    // probes are read once; a new array on every render must not re-run the gate
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handle]);
};
