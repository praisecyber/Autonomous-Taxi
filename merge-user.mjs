import { execSync } from 'child_process';
import readline from 'readline';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

console.log("🚕 Autonomous Taxi - Safe Team Merge Utility\n");

try {
    // Detect the current branch the user is on
    const currentBranch = execSync('git rev-parse --abbrev-ref HEAD', { encoding: 'utf8' }).trim();
    const targetBranch = currentBranch === 'master' ? 'master' : 'main';

    console.log("This script will safely combine the team's latest GitHub code with your local Member 2 files.");
    console.log(`Current local branch: ${currentBranch}\n`);

    rl.question("Ready to begin the merge? (y/n): ", (answer) => {
        if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
            try {
                console.log("\n1️⃣  Fetching latest updates from GitHub...");
                execSync('git fetch origin', { stdio: 'inherit' });

                console.log(`\n2️⃣  Merging origin/${targetBranch} into your local work...`);
                execSync(`git merge origin/${targetBranch}`, { stdio: 'inherit' });

                console.log("\n✅ SUCCESS: The team's code and your code are now safely merged!");
                console.log("Since this script does not push automatically, you can now upload everything to the group repository by typing:");
                console.log(`👉 git push origin ${currentBranch}`);
                
            } catch (error) {
                console.log("\n⚠️  MERGE CONFLICT DETECTED!");
                console.log("Git found overlapping changes between your code and the team's code.");
                console.log("1. Open your files in VS Code and accept/refuse the highlighted changes.");
                console.log("2. Run: git add .");
                console.log('3. Run: git commit -m "Resolve merge conflicts"');
                console.log(`4. Run: git push origin ${currentBranch}`);
            }
        } else {
            console.log("Merge aborted.");
        }
        rl.close();
    });

} catch (err) {
    console.log("❌ Error: Make sure Git is initialized and you have committed your local files first.");
    rl.close();
}