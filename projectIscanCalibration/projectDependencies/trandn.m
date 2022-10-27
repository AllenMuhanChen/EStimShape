function r = trandn()
    % returns a truncated normal distribution
    % mean 0, truncated at -0.5 and 0.5
    r = randn;
    while r > 2 || r < -2
        r = randn;
    end
    r = r/4;
end