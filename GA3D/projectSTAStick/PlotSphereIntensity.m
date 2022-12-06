% PlotSphereIntensity(azimuth, elevation)
% PlotSphereIntensity(azimuth, elevation, intensity)
% h = PlotSphereIntensity(...)
%
% Plots the intensity (as color) of a number of points on a unit sphere.
% Input:
%   azimuth (phi), in radians
%   elevation (theta), in radians
%   intensity (optional, if not provided, a green sphere is produced)
%   All inputs must be vectors or matrices of the same size.
%   Data does not have to be evenly spaced. When there aren't enough points
%   to draw a smooth sphere, additional points (with color) are
%   interpolated.
% Output:
%   h - a handle to the patch object
%
% The axes are also plotted:
%   positive x axis is red
%   positive y axis is green
%   positive z axis is blue
%
% Author: David Johnstone (DSTO, WSD, Australia)
%         david.johnstone@dsto.defence.gov.au
%         Ninh Duong (DSTO, WSD, Australia)
%         ninh.duong@dsto.defence.gov.au
% Date: 18 March, 2008

function varargout = PlotSphereIntensity(hin, az, el, r, varargin)

if (any(size(az) ~= size(el)) || (nargin == 4 && any(size(az) ~= size(varargin{1}))))
    error('input data has inconsistent sizes')
end

% az = az(:) * pi / 180;
% el = el(:) * pi / 180;

if (nargin == 5)
    c = varargin{1};
    c = c(:);
else
    c = ones(length(az),1);
end

% Construct cartesian points (x, y, z) from the given azimuth and elevation
% data, so that each azimuth elevation data pair are a point on the surface
% of a unit sphere.
x = r .* cos(el) .* cos(az);
y = r .* cos(el) .* sin(az);
z = r .* sin(el);

[x,y,z,c] = Sphericalise(x, y, z, c);

% Create a list of facets.
K = convhulln([x y z]);

% Plot the data
h(1) = trisurf(K, x, y, z, c,'parent',hin);
shading(hin,'interp');
axis(hin,'equal')

plotSetting = get(hin, 'NextPlot');
hold(hin,'on');

xAxis = [-1.3 0 0; 1.3 0 0];
yAxis = [0 -1.3 0; 0 1.3 0];
zAxis = [0 0 -1.3; 0 0 1.3];
h(2) = plotAxis(hin,xAxis, 'r', 'LineWidth', 2);
h(3) = plotAxis(hin,yAxis, 'g', 'LineWidth', 2);
h(4) = plotAxis(hin,zAxis, 'b', 'LineWidth', 2);

set(hin, 'NextPlot', plotSetting);

h(5) = text(1.4,0,0.04,'R', 'FontSize', 12,'parent',hin,'color','r');
h(6) = text(0,1.4,0.04,'T', 'FontSize', 12,'parent',hin,'color','g');
h(7) = text(0.04,0.04,1.4,'F', 'FontSize', 12,'parent',hin,'color','b');
h(8) = text(-1.4,0,-0.04,'L', 'FontSize', 12,'parent',hin,'color','r');
h(9) = text(-0.04,-0.04,-1.4,'B', 'FontSize', 12,'parent',hin,'color','b');

if (nargout == 1)
    varargout{1} = h;
end

end

function h = plotAxis(hin, axis, varargin)
h = plot3(hin,axis(:,1), axis(:,2), axis(:,3), varargin{:});
end


% [x2 y2 z2 C2] = Sphericalise(x, y, z, C)
%
% Creates a unit sphere with color data linearly interpolated across it
% based on a given set of points.
% Input:
%    x, y and z are equal sized vectors/matrices and describe the
%        points on a sphere.
%    C is the color data, and is the same size as x, y and z.
%    x, y, z and C must all be the same size. They are used as nx1
%        matrices with x(1), y(1), z(1) describing the location of the
%        first point, and C(1) containing the color for it.
% Output:
%   x, y, z and color so that the data now looks like a unit sphere.

% Method:
%   This algorithm works by triangulating the data and splitting any lines
%   that are longer than a certain threshold (chosen as pi/10 as this gives
%   a fairly smooth sphere.) convhulln is used to triangulate the surface
%   of the sphere, and the indices it returns are used to identify the
%   start and end points of the lines. If the line across the surface of
%   the sphere is too long, a new point is created halfway between the
%   endpoints, and it is scaled to have a magnitude of 1 so that it will
%   lie on the surface of the unit sphere. After all the lines have been
%   checked (and split if necessary), this process is repeated if any lines
%   were split. This repeating must be done as the triangulation will
%   introduce new line segments with the new point, and these may be too
%   long.


function [x2 y2 z2 C2] = Sphericalise(x, y, z, C)

splitLine = 1; % set to 1 initially as we want it to do the loop at least
% once, and MATLAB doesn't have a do while loop

x2 = x(:);
y2 = y(:);
z2 = z(:);
C2 = C(:);

while splitLine
    T = convhulln([x2 y2 z2]);
    
    % It is best to split lines on a per line basis (and not a per triangle
    % basis) as each line is shared by two triangles, so any line that is to be
    % split will be split twice (and the new point will be in the same place)
    lines = unique([T(:,1) T(:,2); T(:,1) T(:,3); T(:,2) T(:,3)], 'rows');

    splitLine = 0;
    for line = lines'

        A = struct('x', x2(line(1)), 'y', y2(line(1)), 'z', z2(line(1)), 'C', C2(line(1)));
        B = struct('x', x2(line(2)), 'y', y2(line(2)), 'z', z2(line(2)), 'C', C2(line(2)));

        % if the length of the geodesic is longer than pi/10
        if acos(dot2(A, B)) > pi/10
            splitLine = 1;
            
            % add point between A and B
            
            % It is possible to calculate elevation and azimuth for A and
            % B, and then interpolate this to get elevation and azimuth for
            % P, and finally convert these back to cartesian coordinates,
            % but this 1) is inefficient and 2) doesn't work around the
            % poles (at least if theta and phi are linearly interpolated).

            P.x = (A.x + B.x) / 2;
            P.y = (A.y + B.y) / 2;
            P.z = (A.z + B.z) / 2;
            magnitude = sqrt(P.x^2 + P.y^2 + P.z^2);
            P.x = P.x / magnitude;
            P.y = P.y / magnitude;
            P.z = P.z / magnitude;
            
            P.C = (A.C + B.C) / 2;
            
            x2(end+1) = P.x;
            y2(end+1) = P.y;
            z2(end+1) = P.z;
            C2(end+1) = P.C;

        end
    end
end

end


function d = dot2(A, B)
d = dot([A.x A.y A.z], [B.x B.y B.z]);
end