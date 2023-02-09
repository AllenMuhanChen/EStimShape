function [verts,faces,norms,th,ph,neighbours] = getIcosphereDeets(doFullSphere,doYRot,doPlot)
    [ x, y, z, faces]=make_icosahedron(2, 1, doFullSphere, 0);
    verts = [x' y' z'];
    
    if doYRot
        R = makehgtform('yrotate',pi/2);
        rotmat = R(1:3,1:3);
        verts = (rotmat * verts')';
    end
    
    if doPlot
        clf;
        h = patch('Vertices',verts,'faces',faces);
        axis equal
        h.FaceAlpha = 0.5;
        view(0,90);
        hold on;
    end
    
    norms = nan(size(faces,1),3);
    for ii=1:size(faces,1)
        v1 = verts(faces(ii,1),:);
        v2 = verts(faces(ii,2),:);
        v3 = verts(faces(ii,3),:);
        norms(ii,:) = v1+v2+v3;
        norms(ii,:) = norms(ii,:) ./ norm(norms(ii,:));
        
        if doPlot
            plot3(v1(1),v1(2),v1(3),'r.','MarkerSize',20);
            plot3(v2(1),v2(2),v2(3),'r.','MarkerSize',20);
            plot3(v3(1),v3(2),v3(3),'r.','MarkerSize',20);
            
            pp = norms(ii,:) .*1.3;
            hold on; line([0 pp(1)],[0 pp(2)],[0 pp(3)]);
        end
    end
    
    [th,ph] = cart2sph(norms(:,1),norms(:,2),norms(:,3));
    
    neighbours = getNeighbours(faces);
    
    if doPlot
        testNeighbours = find(neighbours(1,:));
        for ii=1:length(testNeighbours)
            patch('vertices',verts(faces(testNeighbours(ii),:),:),'faces',[1 2 3],'facecolor','c');
        end
        patch('vertices',verts(faces(1,:),:),'faces',[1 2 3],'facecolor','b');
    end
end

function neighbours = getNeighbours(faces)
    nFaces = size(faces,1);
    neighbours = zeros(nFaces);
    for ii=1:nFaces
        neighbours(ii,sum(faces == faces(ii,1),2)==1) = 1;
        neighbours(ii,sum(faces == faces(ii,2),2)==1) = 1;
        neighbours(ii,sum(faces == faces(ii,3),2)==1) = 1;
    end
end
