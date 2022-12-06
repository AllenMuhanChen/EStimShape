function surfFitParams = getSurfData(data,doPlot)
    % surfData = struct([]);
    surfFitParams = cell(length(data),1);
    for ii=1:length(data)
        vert = data(ii).vert;

        vert = vert .* data(ii).s;
        centerOfMass = (max(vert) + min(vert)) / 2;
        vert = vert - repmat(centerOfMass,size(vert,1),1);
        maxRadDist = max(sqrt(sum(vert.^2,2)));
        vert = vert ./ maxRadDist;

        [minK,maxK,minO,maxO,fitVec] = getSurfCurv(vert,data(ii).face,data(ii).norm);

        % surfData(ii).minK = minK;
        % surfData(ii).maxK = maxK;
        % surfData(ii).minO = minO;
        % surfData(ii).maxO = maxO;
        surfFitParams{ii} = fitVec;
        
        if doPlot
            clf
            h1 = subplot(221);
        %     scatter3(h1,vert(:,1),vert(:,2),vert(:,3),'.')
            axis equal; view(0,90); axis off; hold on;

            h2 = subplot(222);
            scatter3(h2,vert(:,1),vert(:,2),vert(:,3),'.','cdata',minK)
            set(h2,'clim',[-1 1])
            axis equal; view(0,90); axis off; hold on;

            h3 = subplot(223);
            scatter3(h3,vert(:,1),vert(:,2),vert(:,3),'.','cdata',maxK)
            set(h3,'clim',[-1 1])
            axis equal; view(0,90); axis off; hold on;

            h4 = subplot(224);
        %     scatter3(h4,vert(:,1),vert(:,2),vert(:,3),'.')
            axis equal; view(0,90); axis off; hold on;

            vert = vert * 5;
            for jj=1:size(vert,1)

                line([vert(jj,1) vert(jj,1)+minO(jj,1)],[vert(jj,2) vert(jj,2)+minO(jj,2)],[vert(jj,3) vert(jj,3)+minO(jj,3)],'parent',h4);
                line([vert(jj,1) vert(jj,1)+maxO(jj,1)],[vert(jj,2) vert(jj,2)+maxO(jj,2)],[vert(jj,3) vert(jj,3)+maxO(jj,3)],'parent',h1);
            end
        end
    end
end

function [minK,maxK,minO,maxO,fitVec] = getSurfCurv(vert,face,norms)
    nVert = size(vert,1);
    % edge = getEdge(face,nVert);
    
    minK = nan(nVert,1);
    maxK = nan(nVert,1);
    minO = nan(nVert,3);
    maxO = nan(nVert,3);
    
    pos_sp = nan(nVert,3);
    norm_sp = nan(nVert,2);
    minO_sp = nan(nVert,1);
    for ii=1:nVert
        % this vert
        vv = vert(ii,:);
        nn = norms(ii,:);
        
        % get neighbouring verts
        [a,~] = find(face == ii);
        neigIdx = unique(face(a,:));
        neigIdx(neigIdx == ii) = [];
        
        % for each edge with current vert, get curvature
        cc = nan(length(neigIdx),1);
        for jj=1:length(neigIdx)
            vv_n = vert(neigIdx(jj),:);
            nn_n = norms(neigIdx(jj),:);
            
            lEdgeSq = sum((vv-vv_n).^2);
            cc(jj) = dot(nn_n-nn,vv_n-vv) / lEdgeSq;
        end
        
        % assign min and max K and O
        [minK(ii),minIdx] = min(cc);
        [maxK(ii),maxIdx] = max(cc);
        minO(ii,:) = vert(neigIdx(minIdx),:) - vv; minO(ii,:) = minO(ii,:)/norm(minO(ii,:));
        maxO(ii,:) = vert(neigIdx(maxIdx),:) - vv; maxO(ii,:) = maxO(ii,:)/norm(maxO(ii,:));
        
        % clf
        % plot3(vert(:,1),vert(:,2),vert(:,3),'.','color',[0.5 0.5 0.5]); hold on;
        % plot3(vert(1,1),vert(1,2),vert(1,3),'r.','markersize',20);
        % axis equal; view(0,90); axis off; hold on;
        % plot3(vv(1),vv(2),vv(3),'b.','markersize',20)
        % a = vv + nn*0.2;
        % line([vv(1) a(1)],[vv(2) a(2)],[vv(3) a(3)],'color','r'); hold on;
        % a = vv + minO(ii,:)*0.2;
        % line([vv(1) a(1)],[vv(2) a(2)],[vv(3) a(3)],'color','g'); hold on;

        % rotate minO so that it's in plane
        ssc = @(v) [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
        RU = @(A,B) eye(3) + ssc(cross(A,B)) + ssc(cross(A,B))^2*(1-dot(A,B))/(norm(cross(A,B))^2);

        initVec = nn;
        finalVec = [0,0,-1];
        vec2mov = minO(ii,:);
        R = RU(initVec,finalVec);
        vec2mov = R*vec2mov';
        azi = cart2sph(vec2mov(1),vec2mov(2),vec2mov(3)); % ele is 0 and r is 1
     
        % % IMPT: to move the vector back, do this
        % initVec = [0 0 -1];
        % finalVec = nn;
        % [x,y,z] = sph2cart(azi,0,1);
        % vec2mov = [x y z];
        % R = RU(initVec,finalVec);
        % vec2mov = R*vec2mov';
        % 
        % a = vv + vec2mov'*0.2;
        % line([vv(1) a(1)],[vv(2) a(2)],[vv(3) a(3)],'color','m'); hold on;
        
        % get single vector for STA
        % position (th,ph,r), normal (th,ph),  minK, maxK, minO (th,ph)
        [pos_sp(ii,1),pos_sp(ii,2),pos_sp(ii,3)] = cart2sph(vv(1),vv(2),vv(3));
        [norm_sp(ii,1),norm_sp(ii,2)] = cart2sph(nn(1),nn(2),nn(3));
        % minO_sp(ii) = cart2sph(minO(ii,1),minO(ii,2),minO(ii,3));
        minO_sp(ii) = azi;
    end
    
    % curvature smoothing
    coeffs = getGaussian([1/sqrt(2*pi) 0 1],[0 1]) * 2;
    for ii=1:nVert        
        [a,~] = find(face == ii);
        neigIdx = unique(face(a,:));
        neigIdx(neigIdx == ii) = [];
        
        minK(ii) = coeffs(1)*minK(ii) + coeffs(2)*mean(minK(neigIdx));
        maxK(ii) = coeffs(1)*maxK(ii) + coeffs(2)*mean(maxK(neigIdx));
    end
    
    % curvature squashing
    minK = (2./(1+exp(-0.125*minK))) - 1;
    maxK = (2./(1+exp(-0.125*maxK))) - 1;
    
    fitVec = [pos_sp norm_sp minK maxK minO_sp];
    % fitVec = nan(nVert,9);
    % for ii=1:nVert
    %     fitVec(ii,:) = [pos_az,pos_el,pos_r,norm_az,norm_el,minK(ii),maxK(ii),minO_az,minO_el];
    % end
end

% function edge = getEdge(face,nVert)
%     edge = zeros(nVert);
%     for ii=1:size(face,1)
%         tri = nchoosek(face(ii,:),2);
%         edge(sub2ind([nVert nVert],tri(:,1),tri(:,2))) = 1;
%     end
%     edge = (triu(edge) + tril(edge)')>=1;
%     edge = edge + edge';
% end