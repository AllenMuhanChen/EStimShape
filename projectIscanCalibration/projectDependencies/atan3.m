function th = atan3(X,Y)
	% calculates atan(X/Y) in [0,2pi] range

	th = atan2(X,Y);
	th(th < 0) = th(th < 0) + 2*pi;
end