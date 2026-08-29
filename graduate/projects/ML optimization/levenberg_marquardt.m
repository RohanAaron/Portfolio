function result = levenberg_marquardt(Ae, bn, x0, options)
% LEVENBERG_MARQUARDT - Implements the Levenberg-Marquardt method
%
% Inputs:
%   Ae - Jacobian matrix (constant for linear problem)
%   bn - measurement vector
%   x0 - initial guess
%   options - struct with fields:
%       max_iter - maximum iterations (default: 100)
%       tol - gradient tolerance (default: 1e-6)
%       lambda0 - initial damping (default: 1.0)
%       lambda_up - damping increase factor (default: 10)
%       lambda_down - damping decrease factor (default: 0.1)
%       max_retries - max retries per iteration (default: 10)
%       verbose - print progress (default: true)
%
% Output:
%   result - struct with solution and convergence history

% Set default options
if nargin < 4, options = struct(); end
if ~isfield(options, 'max_iter'), options.max_iter = 100; end
if ~isfield(options, 'tol'), options.tol = 1e-6; end
if ~isfield(options, 'lambda0'), options.lambda0 = 1.0; end
if ~isfield(options, 'lambda_up'), options.lambda_up = 10; end
if ~isfield(options, 'lambda_down'), options.lambda_down = 0.1; end
if ~isfield(options, 'max_retries'), options.max_retries = 10; end
if ~isfield(options, 'verbose'), options.verbose = true; end

% Initialize
x = x0;
n = length(x);
lambda = options.lambda0;
lambda_min = 1e-16;
lambda_max = 1e10;
converged = false;

% Storage for history
history.residual_norm = zeros(options.max_iter+1, 1);
history.gradient_norm = zeros(options.max_iter+1, 1);
history.objective = zeros(options.max_iter+1, 1);
history.lambda = zeros(options.max_iter+1, 1);
history.accepted = zeros(options.max_iter, 1);

if options.verbose
    fprintf('\n=== LEVENBERG-MARQUARDT METHOD ===\n');
    fprintf('Iter\t||r||\t\t||g||\t\tlambda\t\tStatus\n');
    fprintf('----\t----\t\t----\t\t------\t\t------\n');
end

% Main iteration loop
for k = 1:options.max_iter
    % Compute residual and gradient
    r = Ae * x - bn;
    f = 0.5 * (r' * r);
    g = Ae' * r;
    
    % Store history
    history.residual_norm(k) = norm(r);
    history.gradient_norm(k) = norm(g);
    history.objective(k) = f;
    history.lambda(k) = lambda;
    
    % Check convergence
    if norm(g) < options.tol
        converged = true;
        if options.verbose
            fprintf('%3d\t%.4e\t%.4e\t%.4e\tCONVERGED\n', k-1, norm(r), norm(g), lambda);
        end
        break;
    end
    
    % Try to find acceptable step with current lambda
    accepted = false;
    retry_count = 0;
    
    while ~accepted && retry_count < options.max_retries
        % Solve damped system: (Ae'*Ae + lambda*I)*p = -Ae'*r
        try
            p = -(Ae' * Ae + lambda * speye(n)) \ g;
        catch
            % If solve fails, increase lambda and retry
            lambda = min(lambda * options.lambda_up, lambda_max);
            retry_count = retry_count + 1;
            continue;
        end
        
        % Evaluate trial point
        x_trial = x + p;
        r_trial = Ae * x_trial - bn;
        f_trial = 0.5 * (r_trial' * r_trial);
        
        % Check if step reduces objective
        if f_trial < f
            % Accept step
            x = x_trial;
            r = r_trial;
            f = f_trial;
            lambda = max(lambda * options.lambda_down, lambda_min);
            accepted = true;
            history.accepted(k) = 1;
            
            if options.verbose && (mod(k-1, 10) == 0)
                fprintf('%3d\t%.4e\t%.4e\t%.4e\tACCEPT\n', k-1, norm(r), norm(g), lambda);
            end
        else
            % Reject step, increase damping
            lambda = min(lambda * options.lambda_up, lambda_max);
            retry_count = retry_count + 1;
            accepted = false;
        end
    end
    
    % If no acceptable step found after max_retries, stop
    if ~accepted
        if options.verbose
            fprintf('%3d\t%.4e\t%.4e\t%.4e\tFAILED (max retries)\n', ...
                k-1, norm(r), norm(g), lambda);
        end
        break;
    end
    
    % Safety check for divergence
    if norm(r) > 1e10 || isnan(norm(r))
        warning('LM: Diverged at iteration %d', k);
        converged = false;
        break;
    end
end

% Compute final values
r_final = Ae * x - bn;
g_final = Ae' * r_final;
f_final = 0.5 * (r_final' * r_final);

% Trim history
history.residual_norm = history.residual_norm(1:k);
history.gradient_norm = history.gradient_norm(1:k);
history.objective = history.objective(1:k);
history.lambda = history.lambda(1:k);
history.accepted = history.accepted(1:k);

% Package results
result.x = x;
result.iterations = k;
result.converged = converged;
result.residual_norm = norm(r_final);
result.gradient_norm = norm(g_final);
result.objective = f_final;
result.history = history;
result.method = 'Levenberg-Marquardt';

if options.verbose
    fprintf('\n--- Final Results ---\n');
    fprintf('Iterations: %d\n', k);
    fprintf('Converged: %s\n', mat2str(converged));
    fprintf('Final ||r||: %.4e\n', norm(r_final));
    fprintf('Final ||g||: %.4e\n', norm(g_final));
    fprintf('Final objective: %.4e\n', f_final);
    fprintf('Acceptance rate: %.1f%%\n', 100*sum(history.accepted)/k);
end

end