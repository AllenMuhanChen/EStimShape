function selectedIds = subsampleVerts(surfFitParams,data)
    doPlot = false;
    parfor ii=1:length(data)
        selectedIds{ii} = serialSelect(surfFitParams{ii});
        
        if doPlot
            figure;
            vert = data(ii).vert;
            patch('vertices',vert,'faces',data(ii).face,'facecolor',[0.5 0.5 0.5])
            axis equal; view(0,90); axis off; hold on;
            plot3(vert(selectedIds{ii},1),vert(selectedIds{ii},2),vert(selectedIds{ii},3),'r.','markersize',20)
        end
    end
end

function selectedIds = serialSelect(surfFitParams_1)
    selectedIds = randi(length(surfFitParams_1));
    for streamCounter=1:length(surfFitParams_1)
        pt = surfFitParams_1(streamCounter,:);
        if isFarEnough(pt,surfFitParams_1(selectedIds,:))
            selectedIds = [selectedIds streamCounter];
        end
    end
    selectedIds = selectedIds(1:4:end);
end

% function farEnough = isFarEnough(p1,selectedPts)
%     thresh = [0.01 pi/4 0.2 0.2 pi/4];
%     
%     farEnough = false(1,size(selectedPts,1));
%     
%     for jj=1:size(selectedPts,1)
%         p2 = selectedPts(jj,:);
%         
%         [x1,y1,z1] = sph2cart(p1(1),p1(2),p1(3));
%         [x2,y2,z2] = sph2cart(p2(1),p2(2),p2(3));
%         
%         euDist = sqrt((x1-x2)^2 + (y1-y2)^2 + (z1-z2)^2);
%         
%         if euDist > thresh(1)
%             [x1,y1,z1] = sph2cart(p1(4),p1(5),1);
%             [x2,y2,z2] = sph2cart(p2(4),p2(5),1);
% 
%             normDist = acos(dot([x1,y1,z1],[x2,y2,z2]));
% 
%             minKDist = p1(6)-p2(6);
%             maxKDist = p1(7)-p2(7);
% 
%             minKDir_1 = getMinKDir([x1,y1,z1],p1(8));
%             minKDir_2 = getMinKDir([x2,y2,z2],p2(8));
%             
%             minKDir = acos(dot(minKDir_1,minKDir_2));
%             
%             if  (normDist > thresh(2)) || ...
%                 (minKDist > thresh(3)) || ...
%                 (maxKDist > thresh(4)) || ...
%                 (minKDir > thresh(5))
%                 farEnough(jj) = true;
%             end
%         end
%     end
%     farEnough = prod(farEnough);
% end

function minKDir = getMinKDir(nor,azi)
    ssc = @(v) [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
    RU = @(A,B) eye(3) + ssc(cross(A,B)) + ssc(cross(A,B))^2*(1-dot(A,B))/(norm(cross(A,B))^2);

    initVec = [0 0 -1];
    finalVec = nor;
    [x,y,z] = sph2cart(azi,0,1);
    minKDir = [x y z];
    R = RU(initVec,finalVec);
    minKDir = R*minKDir';
end

function farEnough = isFarEnough(p1,selectedPts)
    thresh = 3;
    dist = nan(1,size(selectedPts,1));
    for jj=1:size(selectedPts,1)
        p2 = selectedPts(jj,:);
        dist(jj) = sqrt(sum((p1-p2).^2));
    end
    farEnough = all(dist > thresh);
end