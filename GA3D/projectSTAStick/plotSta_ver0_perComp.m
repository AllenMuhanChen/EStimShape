function plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,type)
    switch(type)
        case 's'
            plotS(binSpec,sta,linNum,resp);
        case 'r'
            plotR(binSpec,sta,linNum,resp);
        case 't'
            plotT(binSpec,sta,linNum,resp);
        case 'sr'
            plotSR(binSpec,sta,linNum,resp);
        case 'st'
            plotST(binSpec,sta,linNum,resp);
    end
            
end

function plotS(binSpec,sta,linNum,resp)
    binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.s.binEdges,'uniformoutput',false);
    sta(linNum).s(:) = sta(linNum).s(:)/max(sta(linNum).s(:));
    [b1,b2,b3,b4,b5,b6,b7,b8] = ind2sub(size(sta(linNum).s),find(sta(linNum).s(:)==1));
    
    % figure('name',[num2str(linNum) ' - shafts - 3d position');
    % % ss = sta(linNum).s;
    % % ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    % ss = sta(linNum).s(:,:,:,b4,b5,b6,b7,b8);
    % [th,ph,r] = ndgrid(binCenters{1},binCenters{2},binCenters{3});
    % intensity = ss(:);
    % plotTranslucentScatter2(th(:),ph(:),r(:),intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    % title('3d position')
    
    figure('name',[num2str(linNum) ' - shafts - 3d pos without r']);
    ss = sta(linNum).s(:,:,b3,b4,b5,b6,b7,b8);
    [th,ph] = ndgrid(binCenters{1},binCenters{2});
    th = squeeze(th(:,:,end)); th = th(:);
    ph = squeeze(ph(:,:,end)); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    % figure('name',[num2str(linNum) ' - shafts - 3d pos without r']);
    % plotSphereAsImage(binCenters{1},binCenters{2},ss);
    
    figure('name',[num2str(linNum) ' - shafts - tangent']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).s(b1,b2,b3,:,:,b6,b7,b8);
    th = repmat(binCenters{4}',4,1); th = th(:);
    ph = repmat(binCenters{5},8,1); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    
    figure('name',[num2str(linNum) ' - shafts']); subplot(131);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).s(b1,b2,b3,b4,b5,:,b7,b8);
    intensity = ss(:);
    plot(binCenters{6},intensity);  title([num2str(linNum) ' - shafts - width']); % set(gca,'ylim',[0 0.0005]);
    
    subplot(132);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = squeeze(mean(ss,8));
    ss = sta(linNum).s(b1,b2,b3,b4,b5,b6,:,b8);
    intensity = ss(:);
    plot(binCenters{7},intensity); title([num2str(linNum) ' - shafts - length']); % set(gca,'ylim',[0 0.0005]);
    
    subplot(133);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = squeeze(mean(ss,7));
    ss = sta(linNum).s(b1,b2,b3,b4,b5,b6,b7,:);
    intensity = ss(:);
    plot(binCenters{8},intensity); title([num2str(linNum) ' - shafts - curvature']); % set(gca,'ylim',[0 0.0005]);
end

function plotT(binSpec,sta,linNum,resp)
    binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.t.binEdges,'uniformoutput',false);
    sta(linNum).t(:) = sta(linNum).t(:)/max(sta(linNum).t(:));
    [b1,b2,b3,b4,b5,b6] = ind2sub(size(sta(linNum).t),find(sta(linNum).t(:)==1));
    
    % figure('name',[num2str(linNum) ' - terminals - 3d position');
    % % ss = sta(linNum).s;
    % % ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    % ss = sta(linNum).t(:,:,:,b4,b5,b6);
    % [th,ph,r] = ndgrid(binCenters{1},binCenters{2},binCenters{3});
    % intensity = ss(:);
    % plotTranslucentScatter2(th(:),ph(:),r(:),intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    % title([num2str(linNum) ' - terminals - 3d position')
    
    figure('name',[num2str(linNum) ' - terminals - 3d pos without r']);
    ss = sta(linNum).t(:,:,b3,b4,b5,b6);
    [th,ph] = ndgrid(binCenters{1},binCenters{2});
    th = squeeze(th(:,:,end)); th = th(:);
    ph = squeeze(ph(:,:,end)); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    figure('name',[num2str(linNum) ' - terminals - tangent']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).t(b1,b2,b3,:,:,b6);
    th = repmat(binCenters{4}',4,1); th = th(:);
    ph = repmat(binCenters{5},8,1); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    
    figure('name',[num2str(linNum) ' - terminals - width']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).t(b1,b2,b3,b4,b5,:);
    intensity = ss(:);
    plot(binCenters{6},intensity);  title([num2str(linNum) ' - terminals - width']); % set(gca,'ylim',[0 0.0005]);
end

function plotR(binSpec,sta,linNum,resp)
    binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.r.binEdges,'uniformoutput',false);
    sta(linNum).r(:) = sta(linNum).r(:)/max(sta(linNum).r(:));
    [b1,b2,b3,b4,b5,b6,b7,b8] = ind2sub(size(sta(linNum).r),find(sta(linNum).r(:)==1));
    
    % figure('name',[num2str(linNum) ' - shafts - 3d position');
    % % ss = sta(linNum).s;
    % % ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    % ss = sta(linNum).s(:,:,:,b4,b5,b6,b7,b8);
    % [th,ph,r] = ndgrid(binCenters{1},binCenters{2},binCenters{3});
    % intensity = ss(:);
    % plotTranslucentScatter2(th(:),ph(:),r(:),intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    % title('3d position')
    
    figure('name',[num2str(linNum) ' - roots - 3d pos without r']);
    ss = sta(linNum).r(:,:,b3,b4,b5,b6,b7,b8);
    [th,ph] = ndgrid(binCenters{1},binCenters{2});
    th = squeeze(th(:,:,end)); th = th(:);
    ph = squeeze(ph(:,:,end)); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    figure('name',[num2str(linNum) ' - roots - angle bisector']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).r(b1,b2,b3,:,:,b6,b7,b8);
    th = repmat(binCenters{4}',4,1); th = th(:);
    ph = repmat(binCenters{5},8,1); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    figure('name',[num2str(linNum) ' - roots - angle bisector rotation']);
    ss = sta(linNum).r(b1,b2,b3,b4,b5,b6,b7,:);
    intensity = ss(:);
    plot(binCenters{8},intensity);  title([num2str(linNum) ' - roots - angle bisector rotation']); % set(gca,'ylim',[0 0.0005]);
    
    
    figure('name',[num2str(linNum) ' - roots']); subplot(121);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).r(b1,b2,b3,b4,b5,:,b7,b8);
    intensity = ss(:);
    plot(binCenters{6},intensity);  title([num2str(linNum) ' - roots - width']); % set(gca,'ylim',[0 0.0005]);
    
    subplot(122);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = squeeze(mean(ss,8));
    ss = sta(linNum).r(b1,b2,b3,b4,b5,b6,:,b8);
    intensity = ss(:);
    plot(binCenters{7},intensity); title([num2str(linNum) ' - roots - angle']); % set(gca,'ylim',[0 0.0005]);
    
end

function plotSR(binSpec,sta,linNum,resp)
    binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.sr.binEdges,'uniformoutput',false);
    sta(linNum).sr(:) = sta(linNum).sr(:)/max(sta(linNum).sr(:));
    [b1,b2,b3,b4,b5,b6] = ind2sub(size(sta(linNum).sr),find(sta(linNum).sr(:)==1));
    
    % figure('name',[num2str(linNum) ' - terminals - 3d position');
    % % ss = sta(linNum).sr;
    % % ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    % ss = sta(linNum).t(:,:,:,b4,b5,b6);
    % [th,ph,r] = ndgrid(binCenters{1},binCenters{2},binCenters{3});
    % intensity = ss(:);
    % plotTranslucentScatter2(th(:),ph(:),r(:),intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    % title([num2str(linNum) ' - terminals - 3d position')
    
    figure('name',[num2str(linNum) ' - rooty shafts - 3d pos without r']);
    ss = sta(linNum).sr(:,:,b3,b4,b5,b6);
    [th,ph] = ndgrid(binCenters{1},binCenters{2});
    th = squeeze(th(:,:,end)); th = th(:);
    ph = squeeze(ph(:,:,end)); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    figure('name',[num2str(linNum) ' - rooty shafts - tangent']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).sr(b1,b2,b3,:,:,b6);
    th = repmat(binCenters{4}',4,1); th = th(:);
    ph = repmat(binCenters{5},8,1); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    
    figure('name',[num2str(linNum) ' - rooty shafts - width']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).sr(b1,b2,b3,b4,b5,:);
    intensity = ss(:);
    plot(binCenters{6},intensity);  title([num2str(linNum) ' - rooty shafts - width']); % set(gca,'ylim',[0 0.0005]);
end

function plotST(binSpec,sta,linNum,resp)
    binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.st.binEdges,'uniformoutput',false);
    sta(linNum).st(:) = sta(linNum).st(:)/max(sta(linNum).st(:));
    [b1,b2,b3,b4,b5,b6] = ind2sub(size(sta(linNum).st),find(sta(linNum).st(:)==1));
    
    % figure('name',[num2str(linNum) ' - terminals - 3d position');
    % % ss = sta(linNum).s;
    % % ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    % ss = sta(linNum).t(:,:,:,b4,b5,b6);
    % [th,ph,r] = ndgrid(binCenters{1},binCenters{2},binCenters{3});
    % intensity = ss(:);
    % plotTranslucentScatter2(th(:),ph(:),r(:),intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    % title([num2str(linNum) ' - terminals - 3d position')
    
    figure('name',[num2str(linNum) ' - termy shafts - 3d pos without r']);
    ss = sta(linNum).st(:,:,b3,b4,b5,b6);
    [th,ph] = ndgrid(binCenters{1},binCenters{2});
    th = squeeze(th(:,:,end)); th = th(:);
    ph = squeeze(ph(:,:,end)); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    figure('name',[num2str(linNum) ' - termy shafts - tangent']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,6); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).st(b1,b2,b3,:,:,b6);
    th = repmat(binCenters{4}',4,1); th = th(:);
    ph = repmat(binCenters{5},8,1); ph = ph(:);
    intensity = ss(:);
    plotSphereViews(th,ph,intensity);
    
    
    figure('name',[num2str(linNum) ' - termy shafts - width']);
    % ss = sta(linNum).s;
    % ss = mean(ss,1); ss = mean(ss,2); ss = mean(ss,3); ss = mean(ss,4); ss = mean(ss,5); ss = mean(ss,7); ss = squeeze(mean(ss,8));
    ss = sta(linNum).st(b1,b2,b3,b4,b5,:);
    intensity = ss(:);
    plot(binCenters{6},intensity);  title([num2str(linNum) ' - termy shafts - width']); % set(gca,'ylim',[0 0.0005]);
end

function plotSphereViews(th,ph,intensity)
    subplot(346); hold on; title('front');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    
    subplot(348); hold on; title('back');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',pi);
    set(t,'Matrix',Txy)
    
    subplot(342); hold on; title('top');
    h1 = line([0 0 0],[0 1.3 0],'linewidth',5);
    h2 = PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    t = hgtransform('Parent',gca); set(h1,'Parent',t); set(h2,'Parent',t);
    Txy = makehgtform('xrotate',pi/2);
    set(t,'Matrix',Txy)
    
    subplot(3,4,10); hold on; title('bottom');
    h1 = line([0 0 0],[0 1.3 0],'linewidth',5);
    h2 = PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    t = hgtransform('Parent',gca); set(h1,'Parent',t); set(h2,'Parent',t);
    Txy = makehgtform('xrotate',-pi/2);
    set(t,'Matrix',Txy)
    
    subplot(345); hold on; title('left');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',pi/2);
    set(t,'Matrix',Txy)
    
    subplot(347); hold on; title('right');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, ones(length(th),1), intensity); view(0,90); % set(gca,'clim',[0 0.0005]);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',-pi/2);
    set(t,'Matrix',Txy)
end

function plotSphereAsImage(th_centers,ph_centers,intensity)
    [th,ph] = meshgrid(th_centers,ph_centers);
    [thq,phq] = meshgrid(linspace(-pi,pi,256),linspace(-pi/2,pi/2,128));
    ssq = interp2(th,ph,intensity',thq,phq,'spline');
    
    imagesc(ssq);
    set(gca,'xtick',[1 64:64:256],'ytick',[1 64 128]);
    set(gca,'XTickLabel',{'-\pi' '-\pi/2' '0' '\pi/2' '\pi'});
    set(gca,'YTickLabel',{'-\pi/2' '0' '\pi/2'});
    
%     [~,maxInd] = max(ssq(:));
%     beta = fitAny([thq(:) phq(:)],ssq(:),@getGaussian2d,[thq(maxInd) phq(44) pi/4 pi/4]);
%     figure;
%     drawEllipse(beta(4),beta(2),0,beta(3),beta(1),'r',100,gca)
%     set(gca,'xlim',[-pi pi],'ylim',[-pi/2 pi/2]); axis equal;
end

function z = getGaussian2d(beta,x)
% beta = [mu_x sig_x mu_y sig_y]
    y = x(:,2);
    x = x(:,1);
    
    a = 1;
    mu1 = beta(1);
    sig1 = beta(2);
    mu2 = beta(3);
    sig2 = beta(4);
    
    z = 1/(2*pi*sig1*sig2);
    
    c1 = ((x-mu1).^2)/(2*sig1^2);
    c2 = ((y-mu2).^2)/(2*sig2^2);
    
    z = a * z .* exp(-(c1 + c2));

end