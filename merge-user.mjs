import { execFileSync } from 'child_process';
import readline from 'readline';

function git(args, options = {}) {
    const result = execFileSync('git', args, { encoding: 'utf8', ...options });
    return typeof result === 'string' ? result.trim() : '';
}

function getTargetBranch() {
    try {
        return git(['symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD']);
    } catch {
        for (const branch of ['main', 'master']) {
            try {
                git(['show-ref', '--verify', '--quiet', `refs/remotes/origin/${branch}`]);
                return `origin/${branch}`;
            } catch {
                // Try the other conventional default branch.
            }
        }
        throw new Error('Could not determine origin’s default branch. Fetch origin and set origin/HEAD.');
    }
}

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

console.log("🚕 Autonomous Taxi - Safe Team Merge Utility\n");

try {
    // Detect the current branch the user is on
    const currentBranch = git(['rev-parse', '--abbrev-ref', 'HEAD']);

    console.log("This script will safely combine the team's latest GitHub code with your local Member 2 files.");
    console.log(`Current local branch: ${currentBranch}\n`);

    rl.question("Ready to begin the merge? (y/n): ", (answer) => {
        if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
            try {
                console.log("\n1️⃣  Fetching latest updates from GitHub...");
                git(['fetch', 'origin'], { stdio: 'inherit' });

                const targetBranch = getTargetBranch();
                console.log(`\n2️⃣  Merging ${targetBranch} into your local work...`);
                git(['merge', targetBranch], { stdio: 'inherit' });

                console.log("\n✅ SUCCESS: The team's code and your code are now safely merged!");
                console.log("Since this script does not push automatically, you can now upload everything to the group repository by typing:");
                console.log(`👉 git push origin ${currentBranch}`);
            } catch (error) {
                if (error.status !== undefined && error.status !== 0) {
                    console.error("\n❌ Git operation failed. Review the Git output above and check `git status` for details.");
                } else {
                    console.error(`\n❌ ${error.message}`);
                }
            }
        } else {
            console.log("Merge aborted.");
        }
        rl.close();
    });

} catch (err) {
    console.error(`❌ Unable to start: ${err.message}`);
    rl.close();
}