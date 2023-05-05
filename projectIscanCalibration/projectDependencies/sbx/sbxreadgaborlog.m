function log = sbxreadgaborlog(fname)

fn = [fname '.log_16'];
fid = fopen(fn);

q = fscanf(fid,'%f');
ngabor = q(1);
q = reshape(q(2:end),ngabor*4+2,[])';

L = zeros(size(q,1)*ngabor,5);

m=1;
for k =1:size(q,1)
    for j=0:ngabor-1
        L(m,:) = [q(k,1) q(k,4*j+2) q(k,4*j+3) q(k,4*j+4) q(k,4*j+5)];
        m = m+1;
    end
end

log = table(L(:,1),L(:,2),L(:,3),L(:,4),L(:,5),...
    'VariableNames',{'frame' 'xpos' 'ypos' 'ori' 'phase'});

% align time frames
sbx = load(fname);
ov_frame = L(1:ngabor:end,1);
scanbox_frame = sbx.info.frame(2:end-1);
fit = polyfit(ov_frame,scanbox_frame,1);           % from ov to sbx

t = table(floor(polyval(fit,log.frame)),'VariableName',{'sbxframe'});
log = [log  t];

% make sure the min xpos and ypos are 1

log.xpos = log.xpos - min(log.xpos) + 1;
log.ypos = log.ypos - min(log.ypos) + 1;
