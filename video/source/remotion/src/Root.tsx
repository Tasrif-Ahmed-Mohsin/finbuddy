import React from 'react';
import { Composition } from 'remotion';
import timeline from './timeline.json';
import { Film } from './Video';

export const Root: React.FC = () => (
  <Composition id="Bluefin" component={Film} durationInFrames={(timeline as any).frames} fps={30} width={1920} height={1080} />
);
