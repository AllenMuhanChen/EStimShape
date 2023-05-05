function str = num2semicolonstr(mat)
    % mat will be vectorized before stringing
    mat = mat(:);
    str = mat2str(mat);
    str(1) = ''; 
    str(end) = '';
end