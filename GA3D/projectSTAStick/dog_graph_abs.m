clear; clf; load('~/Desktop/dog/matlab.mat');
h = gca;
% [vert,face]=read_vertices_and_faces_from_obj('/Users/ramanujan/Desktop/dog/dog.obj');
% ralpha = -pi/2;
% rbeta = pi/4;
% rgamma = 0;
% rotmat  = [cos(rbeta)*cos(rgamma), (cos(rgamma)*sin(ralpha)*sin(rbeta) - cos(ralpha)*sin(rgamma)),  (cos(ralpha)*cos(rgamma)*sin(rbeta)+ sin(ralpha)*sin(rgamma)); ...
%             cos(rbeta)*sin(rgamma), (cos(ralpha)*cos(rgamma) + sin(ralpha)*sin(rbeta)*sin(rgamma)), (-cos(rgamma)*sin(ralpha)+cos(ralpha)*sin(rbeta)*sin(rgamma)); ...
%             -sin(rbeta)            ,  cos(rbeta)*sin(ralpha)                                       ,   cos(ralpha)*cos(rbeta)];
% vert = (rotmat*vert')';
plot3(h,vert(:,1),vert(:,2),vert(:,3),'k.','MarkerSize',10);
axis(h,'equal'); view(h,0,90); axis(h,'off'); hold(h,'on');

%%
% for ii=1:7
% dcmObject = datacursormode;
% pause
% datacursormode off
% cursor = getCursorInfo(dcmObject);
% v(ii,:) = cursor.Position;
% plot3(v(:,1),v(:,2),v(:,3),'.','color','r','MarkerSize',10);
% end
% save('~/Desktop/dog/matlab.mat','v');
%% 
% vert = plotSingleStim(gca,'170630_r-190',1,1,22);
% load('~/Desktop/temp/matlab.mat');


%% 
cols = lines(7);
for ii=1:7
    if ii==1
        nPts = 1200;
    else
        nPts = 600;
    end
    [~,idx] = mink(sqrt(sum((repmat(vert(selectVert(ii),:),size(vert,1),1) - vert).^2,2)),nPts);
    col = [linspace(cols(ii,1),0.7,nPts)' linspace(cols(ii,2),0.7,nPts)' linspace(cols(ii,3),0.7,nPts)'];
    hp = scatter3(vert(idx,1),vert(idx,2),vert(idx,3),800,col,'Marker','.');
end