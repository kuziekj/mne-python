% fprintf(logid,'Fixing phase wrap\n');

filename = fullfile(pwd, 'dev' , 'matlab_files', 'data_matlab.mat')
data = load(filename)
data = data.data;

%%%test ppod%%%%%%%%%%%%%%%%%%%%
% data = data(1:80,1:2500);
% 
% temp_dat = data(1:80,1:2500)';
% 
% for i_col = 1:2:80
%     temp1 = temp_dat(:,i_col);
%     temp2 = temp_dat(:,i_col+1);
%     temp_dat(:,i_col) = temp2;
%     temp_dat(:,i_col+1) = temp1;
% end
% 
% if temp_dat == ph
%     disp('PASS');
% else
%     disp('FAIL')
% end
% 
% for i_chan = 1:2:80
%     temp1 = test_poly2(i_chan,:);
%     temp2 = test_poly2(i_chan+1,:);
%     test_poly2(i_chan,:) = temp2;
%     test_poly2(i_chan+1,:) = temp1;
% end
% 
% if test_poly1 == test_poly2(1:80,:)
%     disp('PASS');
% else
%     disp('FAIL')
% end
% 
% 
% for i_chan = 1:2:80
%     temp1 = sd2(i_chan);
%     temp2 = sd2(i_chan+1);
%     sd2(i_chan) = temp2;
%     sd2(i_chan+1) = temp1;
% end
% 
% if sd1 == sd2
%     disp('PASS');
% else
%     disp('FAIL')
% end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% remove first few bad points

n_bad_points = 12
for index = 1:n_bad_points
    data(:,index)=data(:,n_bad_points+1);
end


save(fullfile(pwd, 'dev' , 'matlab_files', 'data_first_bad_python.mat'),'data')

% fix phase wrap

for i_chan=1:size(data,1)
    if mean(data(i_chan,1:50)) < 180
        wrapped_pts=find(data(i_chan,:)>270);
        data(i_chan,wrapped_pts)=data(i_chan,wrapped_pts)-360;
    else
        wrapped_pts=find(data(i_chan,:)<90);
        data(i_chan,wrapped_pts)=data(i_chan,wrapped_pts)+360;
    end
end

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_unwrap_python.mat'),'data')


% data = load("C:\Users\spork\Desktop\data_unwrap_matlab.mat")
% data = data.data;

% detrend data

y=1:size(data,2);
x=y;
% test_poly2 = zeros(80,4);

for i_chan=1:size(data,1)
    poly_coeffs = polyfit(x,data(i_chan,:),3);   % 3 => 3rd order
%     test_poly2(i_chan,:) = poly_coeffs;
    tmp_ph = data(i_chan,:)-polyval(poly_coeffs,x);
    data(i_chan,:)=tmp_ph;
end

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_detrend_python.mat'),'data')

% remove mean here so STD threshold makes sense
%

% data = load("C:\Users\spork\Desktop\data_detrend_matlab.mat")
% data = data.data;

mrph=mean(data,2);
for i_chan=1:size(data,1)
    data(i_chan,:)=(data(i_chan,:)-mrph(i_chan));
end

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_mean_python.mat'),'data')


% remove phase (delay) outliers

% data = load("C:\Users\spork\Desktop\data_mean_matlab.mat")
% data = data.data;

ph_out_thr=3; % always set to "3" per Kathy & Gabriele Oct 12 2012
SDph=std(data(:,n_bad_points:end),[],2);
sd2 = SDph';

for i_chan=1:size(data,1)
    outliers=find(abs(data(i_chan,:))>ph_out_thr*SDph(i_chan));
    if length(outliers)>0
        if outliers(1)==1;
            outliers=outliers(2:end);
        end % can't interp 1st pt
%         if length(outliers)>0
            if outliers(end)==size(data,2) % can't interp last pt
                outliers=outliers(1:end-1);
            end
            n_ph_out(i_chan)=length(outliers);
            for i_pt=1:n_ph_out(i_chan)
                j_pt=outliers(i_pt);
                data(i_chan, j_pt)=(data(i_chan,j_pt-1)+data(i_chan,j_pt+1))/2;
            end
%         end
    end
end

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_outliers_python.mat'),'data')

% normalise data
mrph=mean(data,2);

for i_chan=1:size(data,1)
    data(i_chan,:)=(data(i_chan,:)-mrph(i_chan));
end

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_norm_python.mat'),'data')

% convert to picoseconds

mod_freq = 1.1e8;
data=1e12*data/(360*mod_freq); % convert phase to ps

save(fullfile(pwd, 'dev' , 'matlab_files', 'data_picosec_python.mat'),'data')
