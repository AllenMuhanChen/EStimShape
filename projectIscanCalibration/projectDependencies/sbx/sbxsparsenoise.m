function stat = sbxsparsenoise(fname)

% analyze sparse noise experiment
% example experimnet: fname = 'd:\gm8\gm8_000_002_nonrigid'
% edit Luis 1/10/17. Allow BOTH rigid and nonrigid .signals files as input..
    % -----
    if contains(fname,'rigid') % search for rigid in filename
        si = strfind(fname,'_'); 
        fnamelog = fname( 1:si(end)-1); % remove it
    else 
        fnamelog = fname;
    end
    % -----
    
log = sbxreadsparsenoiselog(fnamelog); % read log
load([fname, '.signals'],'-mat');
dsig = spks;
ncell = size(dsig,2);
nstim = size(log,1);

ntau = 20;

blk = 100;
if ncell<=blk
    blk = ncell;
end

blkidx = cell(0);
idx = 1:ncell;
k = 1;
while(~isempty(idx))
    j = ((k-1)*blk+1): min( ((k-1)*blk+1)+blk-1, ncell);
    blkidx{k} = j;
    k = k+1;
    idx = setdiff(idx,j);
end

for bi = 1:length(blkidx)
    
    ncell = length(blkidx{bi});
    
    r = zeros(max(log.ypos),max(log.xpos),ntau,2,ncell);
    
    fprintf('Processing block #%d',bi);
    
    for(i=1:nstim)
        [i nstim];
        if(log.mean(i)==0)  % rf map for dark spots
            r(log.ypos(i),log.xpos(i),:,1,:) =  squeeze(r(log.ypos(i),log.xpos(i),:,1,:)) + ...
                dsig(log.sbxborn(i)-2:log.sbxborn(i)+ntau-3,blkidx{bi});
        else                % rf map for brigths spots
            r(log.ypos(i),log.xpos(i),:,2,:) =  squeeze(r(log.ypos(i),log.xpos(i),:,2,:)) + ...
                dsig(log.sbxborn(i)-2:log.sbxborn(i)+ntau-3,blkidx{bi});
        end
    end
    
    rf = cell(1,ncell);   
    h = fspecial('gauss',250,40);
    k = 0;
    
    fprintf('Statistics of block #%d\n',bi);    
    for i = 1:size(r,5)
        
        % dark first       
        k = zeros(1,ntau);
        for w=1:ntau
            z = imresize(filter2(h,squeeze(mean(r(:,:,w,1,i),3)),'same'),0.25);
            k(w) = kurtosis(z(:));
        end
        
        m = blkidx{bi}(1)+i-1;
        
        [kmax,t] = max(k);
        stat(m).k_dark = k;
        stat(m).tmax_dark = t;
        stat(m).kmax_dark = kmax;
        stat(m).kern_dark = imresize(filter2(h,squeeze(mean(r(:,:,t,1,i),3)),'same'),0.25);
        
        % bright next        
        k = zeros(1,ntau);
        for w=1:ntau
            z = imresize(filter2(h,squeeze(mean(r(:,:,w,2,i),3)),'same'),0.25);
            k(w) = kurtosis(z(:));
        end
        
        [kmax,t] = max(k);
        stat(m).k_bright = k;
        stat(m).tmax_bright = t;
        stat(m).kmax_bright = kmax;
        stat(m).kern_bright = imresize(filter2(h,squeeze(mean(r(:,:,t,2,i),3)),'same'),0.25);
        
        % est rf center
        ii = NaN;
        jj = NaN;
        ii_bright = NaN;
        ii_dark = NaN;
        jj_bright = NaN;
        jj_dark = NaN;
        
        stat(m).sig = 0;        
        if(stat(m).kmax_dark>8)
            [ii_dark,jj_dark] = find(stat(m).kern_dark == max(stat(m).kern_dark(:)));
        end
        
        if(stat(m).kmax_bright>8)
            [ii_bright,jj_bright] = find(stat(m).kern_bright == max(stat(m).kern_bright(:)));
        end
        
        if(stat(m).kmax_dark>8 && stat(m).kmax_bright>8)
            ktmp = stat(m).kern_dark + stat(m).kern_bright;
            [ii,jj] = find(ktmp == max(ktmp(:)));
            stat(m).sig = 1;
        else 
            ii = nanmean([ii_bright ii_dark]);
            jj = nanmean([jj_bright jj_dark]);
        end
        
        stat(m).x0          = jj(1);
        stat(m).y0          = ii(1);
        stat(m).x0_dark     = jj_dark(1);
        stat(m).y0_dark     = ii_dark(1);
        stat(m).x0_bright   = jj_bright(1);
        stat(m).y0_bright   = ii_bright(1);
        
        % comment if you don't want to plot...
        subplot(2,2,1)
            imagesc(stat(m).kern_dark); axis off
            hold on
            plot(stat(m).x0,stat(m).y0,'kx');
            plot(stat(m).x0_dark,stat(m).y0_dark,'ko');
            hold off
            title(num2str(stat(m).tmax_dark));
            
        subplot(2,2,2)
            imagesc(stat(m).kern_bright);axis off
            hold on
            plot(stat(m).x0,stat(m).y0,'kx');
            plot(stat(m).x0_bright,stat(m).y0_bright,'ko');
            hold off
            title(num2str(stat(m).tmax_bright));
            
        subplot(2,2,3)
            plot(stat(m).k_dark);
            subplot(2,2,4);
            plot(stat(m).k_bright);
            drawnow;
    end
    
end

% edit luis
% get cell body positions
disp('Finding cell body properties...\n');
m = load([fname, '.segment'], '-mat');

p   = regionprops(m.mask, 'centroid', 'Area'); 
p   = [{p(:).Area}', {p(:).Centroid}'];
cbprops = cell2table(p, 'variablenames' ,{'somaarea', 'somacom'});






disp('Saving...');

save([fname '.sparsenoise'],'stat','-v7.3');

disp('Done!');



