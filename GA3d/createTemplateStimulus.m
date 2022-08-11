%% SHAPE

t.shape.x = -1;
t.shape.y = -1;
t.shape.s = -1;
t.shape.color = [1 1 1];
t.shape.texture = 'SHADE';
t.shape.doClouds = false;
t.shape.mstickspec = '';
t.shape.lighting = [0 100 200];
t.shape.lowPass = false;

%% MASK
for ii=1:2
    t.mask(ii).x = -1;
    t.mask(ii).y = -1;
    t.mask(ii).z = -1;
    t.mask(ii).s = -1;
    t.mask(ii).isActive = true;
end

%% OCCLUDER
t.occluder.leftBottom = [-1 -1 -1];
t.occluder.rightTop = [-1 -1 -1];
t.occluder.color = [0 0 0];

%% ID
t.id.tstamp = getPosixTimeNow;
t.id.type = 'blank';
t.id.descId = '';
t.id.genNum = 1;
t.id.linNum = 1;
t.id.stimNum = 1;
t.id.parentId = '';
t.id.parentStim = [];
t.id.isOccluded = false;
t.id.tagForRand = 1;
t.id.tagForMorph = 0;
t.id.radiusProfile = 0;
t.id.isControl = false;
t.id.posthocId = 0;
t.id.saveVertSpec = false;

templateStimulus = t;
save('templateStimulus.mat','templateStimulus');
clearvars t templateStimulus
