function result = gauss_newton(Ae, bn, x0, options)
% GAUSS_NEWTON - Implements the Gauss-Newton method for nonlinear least squares
%
% Inputs:
%   Ae - Jacobian matrix (constant for linear problem)
%   bn - measurement vector
%   x0 - initial guess
%   options - struct with fields:
%       max_iter - maximum iterations (default: 100)
%       tol - gradient tolerance (default: 1e-6)
%       verbose - print progress (default: true)
%
% Output:
%   result - struct with solution and convergence history

% Set default options
if nargin < 4, options = struct(); end
if ~isfield(options, 'max_iter'), options.max_iter = 100; end
if ~isfield(options, 'tol'), options.tol = 1e-6; end
if ~isfield(options, 'verbose'), options.verbose = true; end

% Initialize
x = x0;
n = length(x);
converged = false;

% Storage for history
history.residual_norm = zeros(options.max_iter+1, 1);
history.gradient_norm = zeros(options.max_iter+1, 1);
history.objective = zeros(options.max_iter+1, 1);

if options.verbose
    fprintf('\n=== GAUSS-NEWTON METHOD ===\n');
    fprintf('Iter\t||r||\t\t||g||\t\tStep\n');
    fprintf('----\t----\t\t----\t\t----\n');
end

% Main iteration loop
for k = 1:options.max_iter
    % Compute residual: r = Ae*x - bn
    r = Ae * x - bn;
    
    % Compute objective function value
    f = 0.5 * (r' * r);
    
    % Compute gradient: g = Ae'*r (since J = Ae for linear problem)
    g = Ae' * r;
    
    % Store history
    history.residual_norm(k) = norm(r);
    history.gradient_norm(k) = norm(g);
    history.objective(k) = f;
    
    % Check convergence
    if norm(g) < options.tol
        converged = true;
        if options.verbose
            fprintf('%3d\t%.4e\t%.4e\tCONVERGED\n', k-1, norm(r), norm(g));
        end
        break;
    end
    
    % Solve Gauss-Newton equation: (Ae'*Ae)*p = -Ae'*r
    % Using MATLAB's backslash (automatically chooses best method)
    try
        p = -(Ae' * Ae) \ g;
    catch
        warning('GN: Failed to solve linear system at iteration %d', k);
        converged = false;
        break;
    end
    
    % Update: x_new = x + p (full step)
    x = x + p;
    
    % Print progress every 10 iterations
    if options.verbose && (mod(k-1, 10) == 0)
        fprintf('%3d\t%.4e\t%.4e\t%.4e\n', k-1, norm(r), norm(g), norm(p));
    end
    
    % Safety check for divergence
    if norm(r) > 1e10 || isnan(norm(r))
        warning('GN: Diverged at iteration %d', k);
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

% Package results
result.x = x;
result.iterations = k;
result.converged = converged;
result.residual_norm = norm(r_final);
result.gradient_norm = norm(g_final);
result.objective = f_final;
result.history = history;
result.method = 'Gauss-Newton';

if options.verbose
    fprintf('\n--- Final Results ---\n');
    fprintf('Iterations: %d\n', k);
    fprintf('Converged: %s\n', mat2str(converged));
    fprintf('Final ||r||: %.4e\n', norm(r_final));
    fprintf('Final ||g||: %.4e\n', norm(g_final));
    fprintf('Final objective: %.4e\n', f_final);
end

end