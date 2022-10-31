function log = sbxreadsparsenoiselog(fname)

fn = [fname '.log_02'];
log = load(fn);

log = table(log(:,1),log(:,2),log(:,3),log(:,4),log(:,5),log(:,6),log(:,7),...
    'VariableNames',{'frame' 'xpos' 'ypos' 'mean' 'maxage' 'born' 'radius'});


% align time frames
sbx = load(fname);
scanbox_frame = sbx.info.frame(2:end-1);
ov_frame = 0:60:(length(scanbox_frame)-1)*60;
fit = polyfit(ov_frame',scanbox_frame,1);           % from ov to sbx

t = table(floor(polyval(fit,log.born)),'VariableName',{'sbxborn'});
log = [log  t];
[~,idx] = sort(log.sbxborn);
log = log(idx,:);

% make sure the min xpos and ypos are 1

log.xpos = log.xpos - min(log.xpos) + 1;
log.ypos = log.ypos - min(log.ypos) + 1;
