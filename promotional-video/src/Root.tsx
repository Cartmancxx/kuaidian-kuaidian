import React from 'react';
import {Composition} from 'remotion';
import {Film} from './Film';
export const Root: React.FC=()=> <Composition id="LaunchFilm" component={Film} durationInFrames={960} fps={30} width={1920} height={1080} defaultProps={{bgm:true}}/>;
