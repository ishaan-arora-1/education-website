const x1 = require('@actions/core');
const x2 = require('@actions/github');

const y1 = async () => {
    try {
        console.log("Initiating process...");

        const t1 = x1.getInput('repo-token', { required: true });
        const t2 = x2.getOctokit(t1);

        const { eventName: e1, payload: p1, repo: r1 } = x2.context;
        const { issue: i1, comment: c1 } = p1;
        const r2 = `${r1.owner}/${r1.repo}`;
        const [r3, r4] = r2.split('/');

        console.log(`Handling event: ${e1} in repository ${r2}`);

        const k1 = [
            'i am interested in contributing', 'i am interested in doing this', 'i can try fixing this',
            'work on this', 'be assigned this', 'assign me this', 'assign it to me',
            'assign this to me', 'assign to me', '/assign'
        ];
        const k2 = ['/unassign'];

        if (e1 === 'issue_comment' && i1 && c1) {
            console.log('Processing comment...');
            const s1 = c1.body.toLowerCase();
            const f1 = k1.some(k => s1.includes(k));
            const f2 = k2.some(k => s1.startsWith(k));

            if (f2) {
                console.log(`Removing assignment of issue #${i1.number} from ${c1.user.login}`);

                try {
                    const d1 = await t2.issues.get({
                        owner: r3,
                        repo: r4,
                        issue_number: i1.number
                    });

                    const f3 = d1.data.labels.some(l => l.name === "assigned");

                    if (f3) {
                        await t2.issues.removeAssignees({
                            owner: r3,
                            repo: r4,
                            issue_number: i1.number,
                            assignees: [c1.user.login]
                        });

                        await t2.issues.removeLabel({
                            owner: r3,
                            repo: r4,
                            issue_number: i1.number,
                            name: "assigned"
                        }).catch(() => console.log("Label missing or already deleted."));

                        const e2 = await t2.issues.listComments({
                            owner: r3,
                            repo: r4,
                            issue_number: i1.number
                        });

                        const f4 = e2.data.some(c =>
                            c.body.includes('⏳ Auto-unassigned due to inactivity.') ||
                            c.body.includes('You are now unassigned from this issue.')
                        );

                        if (!f4) {
                            await t2.issues.createComment({
                                owner: r3,
                                repo: r4,
                                issue_number: i1.number,
                                body: `You have been unassigned. This task is now available for others. Type /assign if you'd like to take it again.`
                            });
                        }
                    } else {
                        console.log(`Issue #${i1.number} lacks "assigned" label, skipping.`);
                    }
                } catch (e) {
                    console.error(`Failed to unassign issue #${i1.number}:`, e);
                }
            }

            if (f1) {
                console.log(`Assigning issue #${i1.number} to ${c1.user.login}`);
                try {
                    const u1 = c1.user.login;

                    const a1 = await t2.paginate(t2.issues.listForRepo, {
                        owner: r3,
                        repo: r4,
                        state: 'open',
                        assignee: u1
                    });

                    let a2 = [];
                    for (const a3 of a1) {
                        if (a3.number === i1.number) continue;

                        const q1 = `type:pr state:open repo:${r3}/${r4} ${a3.number} in:body`;
                        const p2 = await t2.search.issuesAndPullRequests({ q: q1 });

                        if (p2.data.total_count === 0) {
                            console.log(`Issue #${a3.number} lacks an open PR`);
                            a2.push(a3.number);
                        }
                    }

                    if (a2.length > 0) {
                        const i2 = a2.join(', #');
                        await t2.issues.createComment({
                            owner: r3,
                            repo: r4,
                            issue_number: i1.number,
                            body: `You can't take this task yet. You still have uncompleted issues: #${i2}. Please complete them before requesting another.`
                        });
                        return;
                    }

                    await t2.issues.addAssignees({
                        owner: r3,
                        repo: r4,
                        issue_number: i1.number,
                        assignees: [u1]
                    });

                    await t2.issues.addLabels({
                        owner: r3,
                        repo: r4,
                        issue_number: i1.number,
                        labels: ["assigned"]
                    });

                    await t2.issues.createComment({
                        owner: r3,
                        repo: r4,
                        issue_number: i1.number,
                        body: `Hey @${u1}! You're assigned to [${r2} issue #${i1.number}](https://github.com/${r2}/issues/${i1.number}). Please finish your PR within 1 day.`
                    });

                } catch (e) {
                    console.error(`Failed to assign issue #${i1.number}:`, e);
                }
            }
        }

        console.log('Reviewing inactive assignments...');
        const d2 = new Date();

        try {
            const e3 = await t2.paginate(t2.issues.listEventsForRepo, {
                owner: r3,
                repo: r4,
                per_page: 100,
            }, r => r.data.filter(e => e.event === "assigned"));

            for (const e4 of e3) {
                if (e4.issue.assignee && e4.issue.state === "open") {
                    const t3 = d2.getTime() - new Date(e4.issue.updated_at).getTime();
                    const d3 = t3 / (1000 * 3600 * 24);

                    if (d3 > 1) {
                        console.log(`Revoking assignment of issue #${e4.issue.number} due to 1 day of inactivity`);

                        const d4 = await t2.issues.get({
                            owner: r3,
                            repo: r4,
                            issue_number: e4.issue.number
                        });

                        const f5 = d4.data.labels.some(l => l.name === "assigned");

                        if (f5) {
                            await t2.issues.removeAssignees({
                                owner: r3,
                                repo: r4,
                                issue_number: e4.issue.number,
                                assignees: [e4.issue.assignee.login]
                            });

                            await t2.issues.removeLabel({
                                owner: r3,
                                repo: r4,
                                issue_number: e4.issue.number,
                                name: "assigned"
                            });

                            await t2.issues.createComment({
                                owner: r3,
                                repo: r4,
                                issue_number: e4.issue.number,
                                body: `⏳ Task unassigned due to inactivity. Available for reassignment.`
                            });
                        } else {
                            console.log(`Issue #${e4.issue.number} lacks "assigned" label, skipping.`);
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Failed to process inactive assignments:", e);
        }

    } catch (e) {
        console.error("Critical failure in execution:", e);
    }
};

y1();
