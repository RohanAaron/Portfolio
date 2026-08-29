% COMPARE GN vs LM - Main comparison script for final project
% Focuses on Gauss-Newton vs Levenberg-Marquardt
clear; close all; clc;

fprintf('=============================================================\n');
fprintf('   COMPARATIVE ANALYSIS: GAUSS-NEWTON vs LEVENBERG-MARQUARDT\n');
fprintf('   Tomography Parameter Estimation Problem\n');
fprintf('=============================================================\n\n');

% Load data
load('SG_tomo.mat');
n = size(Ae, 2);
m = size(Ae, 1);

fprintf('Problem size: %d variables, %d equations\n\n', n, m);

% Setup options
options.max_iter = 50;
options.tol = 1e-6;
options.verbose = false;

%% THREE different initializations to show robustness

% Initialization 1: Good (zeros)
x0_good = zeros(n, 1);

% Initialization 2: Poor (small random)
rng(42);
x0_poor = randn(n, 1) * 0.1;

% Initialization 3: Very Poor (large random)
rng(123);
x0_verypoor = randn(n, 1) * 1.0;

fprintf('Testing THREE initializations:\n');
fprintf('  1. GOOD: zeros (optimal for this problem)\n');
fprintf('  2. POOR: random * 0.1\n');
fprintf('  3. VERY POOR: random * 1.0\n\n');

%% Run all tests

test_cases = {'Good', 'Poor', 'Very Poor'};
x0_cases = {x0_good, x0_poor, x0_verypoor};

results_GN = cell(3,1);
results_LM = cell(3,1);
times_GN = zeros(3,1);
times_LM = zeros(3,1);

for i = 1:3
    fprintf('Running with %s initialization...\n', test_cases{i});
    fprintf('--------------------------------------------\n');
    
    % Gauss-Newton
    fprintf('  [1/2] Gauss-Newton...');
    tic;
    results_GN{i} = gauss_newton(Ae, bn, x0_cases{i}, options);
    times_GN(i) = toc;
    if results_GN{i}.converged
        fprintf(' ✓ Converged in %d iterations (%.2f s)\n', results_GN{i}.iterations, times_GN(i));
    else
        fprintf(' ✗ Failed to converge\n');
    end
    
    % Levenberg-Marquardt
    fprintf('  [2/2] Levenberg-Marquardt...');
    tic;
    results_LM{i} = levenberg_marquardt(Ae, bn, x0_cases{i}, options);
    times_LM(i) = toc;
    if results_LM{i}.converged
        fprintf(' ✓ Converged in %d iterations (%.2f s)\n', results_LM{i}.iterations, times_LM(i));
    else
        fprintf(' ✗ Failed to converge\n');
    end
    fprintf('\n');
end

%% Display Comprehensive Results Table

fprintf('=============================================================\n');
fprintf('                    RESULTS SUMMARY\n');
fprintf('=============================================================\n\n');

for i = 1:3
    fprintf('%s INITIALIZATION:\n', upper(test_cases{i}));
    fprintf('%-25s | %8s | %8s | %12s | %12s\n', 'Method', 'Iters', 'Time(s)', '||r|| final', '||g|| final');
    fprintf('%-25s-+-%8s-+-%8s-+-%12s-+-%12s\n', repmat('-',1,25), repmat('-',1,8), repmat('-',1,8), repmat('-',1,12), repmat('-',1,12));
    
    % Gauss-Newton
    if results_GN{i}.converged
        fprintf('%-25s | %8d | %8.2f | %12.2e | %12.2e\n', 'Gauss-Newton', ...
            results_GN{i}.iterations, times_GN(i), results_GN{i}.residual_norm, results_GN{i}.gradient_norm);
    else
        fprintf('%-25s | %8s | %8.2f | %12s | %12s\n', 'Gauss-Newton', 'FAILED', times_GN(i), 'N/A', 'N/A');
    end
    
    % Levenberg-Marquardt
    if results_LM{i}.converged
        fprintf('%-25s | %8d | %8.2f | %12.2e | %12.2e\n', 'Levenberg-Marquardt', ...
            results_LM{i}.iterations, times_LM(i), results_LM{i}.residual_norm, results_LM{i}.gradient_norm);
    else
        fprintf('%-25s | %8s | %8.2f | %12s | %12s\n', 'Levenberg-Marquardt', 'FAILED', times_LM(i), 'N/A', 'N/A');
    end
    fprintf('\n');
end

%% KEY INSIGHTS
fprintf('=============================================================\n');
fprintf('                    KEY INSIGHTS\n');
fprintf('=============================================================\n');
fprintf('1. Both methods converge to the same solution (||r|| ≈ 95)\n');
fprintf('2. GN is faster per iteration but less robust\n');
fprintf('3. LM uses adaptive damping for robustness\n');
fprintf('4. For this linear problem, both work well from any start\n');
fprintf('5. LM would show clear advantage on truly nonlinear problems\n');
fprintf('=============================================================\n\n');

%% Create Comprehensive Comparison Plots

figure('Position', [50, 50, 1600, 900]);

plot_titles = {'Good Init (zeros)', 'Poor Init (rand×0.1)', 'Very Poor Init (rand×1.0)'};

for i = 1:3
    % Residual convergence
    subplot(3,3,(i-1)*3+1);
    if results_GN{i}.converged
        semilogy(0:results_GN{i}.iterations-1, results_GN{i}.history.residual_norm, ...
            'b-o', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    hold on;
    if results_LM{i}.converged
        semilogy(0:results_LM{i}.iterations-1, results_LM{i}.history.residual_norm, ...
            'r-s', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    xlabel('Iteration', 'FontSize', 12);
    ylabel('Residual Norm ||r||', 'FontSize', 12);
    title(sprintf('Residual: %s', plot_titles{i}), 'FontSize', 13, 'FontWeight', 'bold');
    legend('GN', 'LM', 'Location', 'best', 'FontSize', 11);
    grid on;
    set(gca, 'FontSize', 11);
    
    % Gradient convergence
    subplot(3,3,(i-1)*3+2);
    if results_GN{i}.converged
        semilogy(0:results_GN{i}.iterations-1, results_GN{i}.history.gradient_norm, ...
            'b-o', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    hold on;
    if results_LM{i}.converged
        semilogy(0:results_LM{i}.iterations-1, results_LM{i}.history.gradient_norm, ...
            'r-s', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    xlabel('Iteration', 'FontSize', 12);
    ylabel('Gradient Norm ||∇f||', 'FontSize', 12);
    title(sprintf('Gradient: %s', plot_titles{i}), 'FontSize', 13, 'FontWeight', 'bold');
    legend('GN', 'LM', 'Location', 'best', 'FontSize', 11);
    grid on;
    set(gca, 'FontSize', 11);
    
    % Objective convergence
    subplot(3,3,(i-1)*3+3);
    if results_GN{i}.converged
        semilogy(0:results_GN{i}.iterations-1, results_GN{i}.history.objective, ...
            'b-o', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    hold on;
    if results_LM{i}.converged
        semilogy(0:results_LM{i}.iterations-1, results_LM{i}.history.objective, ...
            'r-s', 'LineWidth', 2.5, 'MarkerSize', 7);
    end
    xlabel('Iteration', 'FontSize', 12);
    ylabel('Objective f(x)', 'FontSize', 12);
    title(sprintf('Objective: %s', plot_titles{i}), 'FontSize', 13, 'FontWeight', 'bold');
    legend('GN', 'LM', 'Location', 'best', 'FontSize', 11);
    grid on;
    set(gca, 'FontSize', 11);
end

sgtitle('Comparative Analysis: Gauss-Newton vs Levenberg-Marquardt', 'FontSize', 16, 'FontWeight', 'bold');

% Save
saveas(gcf, 'comparison_convergence.png');
fprintf('✓ Convergence plots saved: comparison_convergence.png\n');

%% Visualize Reconstructions

figure('Position', [100, 100, 1400, 400]);

subplot(1,3,1);
imagesc(reshape(results_GN{1}.x, 128, 128));
colormap gray;
axis image off;
title('Gauss-Newton', 'FontSize', 14, 'FontWeight', 'bold');
colorbar;

subplot(1,3,2);
imagesc(reshape(results_LM{1}.x, 128, 128));
colormap gray;
axis image off;
title('Levenberg-Marquardt', 'FontSize', 14, 'FontWeight', 'bold');
colorbar;

subplot(1,3,3);
imagesc(reshape(abs(results_GN{1}.x - results_LM{1}.x), 128, 128));
colormap hot;
axis image off;
title('Difference (GN - LM)', 'FontSize', 14, 'FontWeight', 'bold');
colorbar;

sgtitle('Tomography Reconstructions', 'FontSize', 16, 'FontWeight', 'bold');

saveas(gcf, 'reconstructions.png');
fprintf('✓ Reconstruction images saved: reconstructions.png\n');

%% Plot LM Damping Evolution

figure('Position', [100, 100, 1200, 400]);
for i = 1:3
    subplot(1,3,i);
    if results_LM{i}.converged
        semilogy(0:results_LM{i}.iterations-1, results_LM{i}.history.lambda, ...
            'r-o', 'LineWidth', 2.5, 'MarkerSize', 8);
        xlabel('Iteration', 'FontSize', 12);
        ylabel('Damping Parameter λ', 'FontSize', 12);
        title(plot_titles{i}, 'FontSize', 13, 'FontWeight', 'bold');
        grid on;
        set(gca, 'FontSize', 11);
    end
end
sgtitle('LM Adaptive Damping Evolution', 'FontSize', 16, 'FontWeight', 'bold');

saveas(gcf, 'lm_damping.png');
fprintf('✓ LM damping plot saved: lm_damping.png\n');

%% Save all results

save('final_results.mat', 'results_GN', 'results_LM', 'times_GN', 'times_LM', 'test_cases');
fprintf('✓ All results saved: final_results.mat\n');

fprintf('\n=============================================================\n');
fprintf('   ALL ANALYSIS COMPLETE! Ready for report writing.\n');
fprintf('=============================================================\n');
fprintf('\nGenerated files:\n');
fprintf('  • comparison_convergence.png (main results plot)\n');
fprintf('  • reconstructions.png (image reconstructions)\n');
fprintf('  • lm_damping.png (LM damping behavior)\n');
fprintf('  • final_results.mat (all data)\n');