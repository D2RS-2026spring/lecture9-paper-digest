const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/gaoch/.claude/skills/pptx/scripts/html2pptx');
const path = require('path');

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = '高老师';
    pptx.title = '漫谈 Vibe Coding';
    pptx.subject = 'AI时代的科研开发范式转变';

    const slidesDir = path.join(__dirname, 'slides');

    // Slide 1: 封面
    await html2pptx(path.join(slidesDir, 'slide01.html'), pptx);
    console.log('✓ Slide 1: 封面');

    // Slide 2: 结课安排
    await html2pptx(path.join(slidesDir, 'slide02.html'), pptx);
    console.log('✓ Slide 2: 结课安排');

    // Slide 3: 内容回顾
    await html2pptx(path.join(slidesDir, 'slide03.html'), pptx);
    console.log('✓ Slide 3: 内容回顾');

    // Slide 4: Paper Digest项目 (带链接)
    const slide4 = pptx.addSlide();
    slide4.background = { color: 'F7FAFC' };

    // 标题
    slide4.addShape(pptx.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.6, fill: { color: '1A365D' } });
    slide4.addText('Paper Digest 项目演示：Vibe Coding 实战', { x: 0.4, y: 0.15, w: 9, h: 0.4, color: 'FFFFFF', fontSize: 18, bold: true });

    // 左侧流程
    slide4.addText('开发流程闭环', { x: 0.4, y: 0.9, w: 4, h: 0.3, color: '1A365D', fontSize: 12, bold: true, border: { pt: 0, pb: 2, color: '4299E1' } });

    const steps = [
        { num: '1', text: '需求讨论：与 ChatGPT 确定系统架构', hasLink: true, url: 'https://chatgpt.com/share/69c9d325-7220-8323-99e2-db2dd7dd7e29', linkText: 'chatgpt.com/share/...' },
        { num: '2', text: '规则先行：提供开发文档，确保 AI 开发有章可循', hasLink: false },
        { num: '3', text: '原型验证：使用 Quarto 文档进行分步实现，完成原型设计和 README', hasLink: false },
        { num: '4', text: 'Agent 开发：使用 Claude Code + Kimi K2.5 花费约 60 元 Token 开发完成', hasLink: false },
        { num: '5', text: '人工干预：中途必要时进行干预，参与开发过程，确保科学性', hasLink: false }
    ];

    let yPos = 1.35;
    steps.forEach(step => {
        // 圆形数字
        slide4.addShape(pptx.shapes.OVAL, { x: 0.4, y: yPos, w: 0.25, h: 0.25, fill: { color: '4299E1' } });
        slide4.addText(step.num, { x: 0.4, y: yPos + 0.02, w: 0.25, h: 0.2, align: 'center', color: 'FFFFFF', fontSize: 10, bold: true });

        // 文本
        slide4.addText(step.text, { x: 0.75, y: yPos, w: 3.5, h: step.hasLink ? 0.2 : 0.35, color: '2D3748', fontSize: 9 });

        // 链接
        if (step.hasLink) {
            slide4.addText(step.linkText, {
                x: 0.75, y: yPos + 0.2, w: 3.5, h: 0.15,
                color: '2B6CB0', fontSize: 7,
                hyperlink: { url: step.url, tooltip: '点击查看' }
            });
        }
        yPos += 0.55;
    });

    // 右侧卡片
    slide4.addText('技术栈', { x: 4.8, y: 0.9, w: 4.8, h: 0.25, color: '1A365D', fontSize: 10, bold: true, fill: { color: 'FFFFFF' }, inset: 0.1, line: { color: '4299E1', pt: 2 } });
    slide4.addText('Python、Zotero、LLM（Qwen-Long）', { x: 4.8, y: 1.2, w: 4.8, h: 0.3, color: '4A5568', fontSize: 9, fill: { color: 'FFFFFF' }, inset: 0.1 });

    slide4.addText('开发截图', { x: 4.8, y: 1.6, w: 4.8, h: 0.25, color: '1A365D', fontSize: 10, bold: true, fill: { color: 'FFFFFF' }, inset: 0.1, line: { color: '4299E1', pt: 2 } });
    slide4.addText('详见下页截图展示', { x: 4.8, y: 1.9, w: 4.8, h: 0.3, color: '4A5568', fontSize: 9, fill: { color: 'FFFFFF' }, inset: 0.1 });

    slide4.addText('开发历程', { x: 4.8, y: 2.3, w: 4.8, h: 0.25, color: '1A365D', fontSize: 10, bold: true, fill: { color: 'FFFFFF' }, inset: 0.1, line: { color: '4299E1', pt: 2 } });
    slide4.addText('GitHub Commit History 完整记录开发过程', { x: 4.8, y: 2.6, w: 4.8, h: 0.2, color: '4A5568', fontSize: 9, fill: { color: 'FFFFFF' }, inset: 0.1 });
    slide4.addText('github.com/D2RS-2026spring/lecture9-paper-digest/commits/main', {
        x: 4.8, y: 2.85, w: 4.8, h: 0.15, color: '2B6CB0', fontSize: 7,
        hyperlink: { url: 'https://github.com/D2RS-2026spring/lecture9-paper-digest/commits/main/', tooltip: '查看提交历史' }
    });

    console.log('✓ Slide 4: Paper Digest 项目 (含可点击链接)');

    // Slide 5-7: 图片和常规幻灯片
    await html2pptx(path.join(slidesDir, 'slide05-img.html'), pptx);
    console.log('✓ Slide 5: 开发过程截图');

    await html2pptx(path.join(slidesDir, 'slide05.html'), pptx);
    console.log('✓ Slide 6: 数据科学思维');

    await html2pptx(path.join(slidesDir, 'slide06.html'), pptx);
    console.log('✓ Slide 7: 职业展望');

    // Slide 8: Token 出海 (带链接)
    const slide8 = pptx.addSlide();
    slide8.background = { color: 'F7FAFC' };

    slide8.addShape(pptx.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.55, fill: { color: '1A365D' } });
    slide8.addText('幕后补给：Token 出海与批发 (Coding Plan)', { x: 0.4, y: 0.15, w: 9, h: 0.35, color: 'FFFFFF', fontSize: 16, bold: true });

    slide8.addShape(pptx.shapes.RECTANGLE, { x: 0.4, y: 0.75, w: 9.2, h: 0.45, fill: { color: '1A365D' } });
    slide8.addText('Vibe Coding 的大规模应用，依赖于极低成本的 Token 供应 | Token = AI 时代的算力燃料', { x: 0.5, y: 0.82, w: 9, h: 0.35, color: 'FFFFFF', fontSize: 10 });

    slide8.addText('国内主流模型提供商（Coding Plan 优惠）', { x: 0.4, y: 1.35, w: 5, h: 0.25, color: '2D3748', fontSize: 11, bold: true, border: { pt: 0, pl: 2, color: '4299E1' } });

    const providers = [
        { name: '阿里云百炼', url: 'https://bailian.console.aliyun.com/cn-beijing?spm=5176.45659035.0.0.174f6256FCLz8w&tab=coding-plan#/efm/coding-plan-index', linkText: 'bailian.console.aliyun.com' },
        { name: '智谱 AI', url: 'https://docs.bigmodel.cn/cn/coding-plan/overview', linkText: 'docs.bigmodel.cn' },
        { name: '火山引擎', url: 'https://www.volcengine.com/activity/codingplan', linkText: 'volcengine.com' },
        { name: 'MinMax', url: 'https://platform.minimaxi.com/docs/guides/pricing-token-plan', linkText: 'platform.minimaxi.com' }
    ];

    let yProv = 1.75;
    providers.forEach((prov, idx) => {
        slide8.addShape(pptx.shapes.RECTANGLE, { x: 0.4, y: yProv, w: 5, h: 0.4, fill: { color: 'FFFFFF' }, line: { color: 'E2E8F0', pt: 0.5 } });
        slide8.addText(prov.name, { x: 0.5, y: yProv + 0.08, w: 1.5, h: 0.25, color: '1A365D', fontSize: 10, bold: true });
        slide8.addText(prov.linkText, {
            x: 2.2, y: yProv + 0.1, w: 3, h: 0.2, color: '2B6CB0', fontSize: 8,
            hyperlink: { url: prov.url, tooltip: '访问 ' + prov.name }
        });
        yProv += 0.48;
    });

    slide8.addText('充分利用国内云厂商的 Coding Plan 优惠，大幅降低 Token 成本', { x: 0.4, y: 3.7, w: 5, h: 0.2, color: '718096', fontSize: 8, align: 'center' });

    slide8.addShape(pptx.shapes.RECTANGLE, { x: 5.8, y: 1.35, w: 3.8, h: 0.35, fill: { color: 'FED7D7' } });
    slide8.addText('中国出口新动向 - Token 批发', { x: 5.8, y: 1.4, w: 3.8, h: 0.25, color: 'C53030', fontSize: 10, bold: true, align: 'center' });
    slide8.addShape(pptx.shapes.RECTANGLE, { x: 5.8, y: 1.8, w: 3.8, h: 2, fill: { color: '1A365D' } });
    slide8.addText('相关截图详见后续页面', { x: 6, y: 2.5, w: 3.4, h: 0.3, color: 'FFFFFF', fontSize: 11, align: 'center' });
    slide8.addText('Token 出海 | Coding Plan | 价格对比', { x: 6, y: 2.9, w: 3.4, h: 0.2, color: 'A8D1F0', fontSize: 9, align: 'center' });

    console.log('✓ Slide 8: Token 出海 (含可点击链接)');

    // Slide 9-11: 图片幻灯片
    await html2pptx(path.join(slidesDir, 'slide08-img.html'), pptx);
    console.log('✓ Slide 9: Token 出海截图');
    await html2pptx(path.join(slidesDir, 'slide09-img.html'), pptx);
    console.log('✓ Slide 10: Coding Plan 截图');
    await html2pptx(path.join(slidesDir, 'slide10-img.html'), pptx);
    console.log('✓ Slide 11: 价格对比截图');

    // Slide 12: Claude Code配置 (带链接)
    const slide12 = pptx.addSlide();
    slide12.background = { color: 'F7FAFC' };

    slide12.addShape(pptx.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.7, fill: { color: '1A365D' } });
    slide12.addText('进阶实操：Claude Code 配置', { x: 0.5, y: 0.2, w: 9, h: 0.4, color: 'FFFFFF', fontSize: 20, bold: true });

    slide12.addShape(pptx.shapes.RECTANGLE, { x: 0.5, y: 1, w: 4, h: 2.2, fill: { color: '1A365D' } });
    slide12.addText('什么是 Claude Code？', { x: 0.6, y: 1.1, w: 3.8, h: 0.25, color: 'A8D1F0', fontSize: 12, bold: true });
    slide12.addText('Claude Code 是 Anthropic 推出的 AI 编程助手，能够：', { x: 0.6, y: 1.45, w: 3.8, h: 0.25, color: 'FFFFFF', fontSize: 10 });
    slide12.addText('• 理解大型代码库，进行智能代码导航', { x: 0.8, y: 1.8, w: 3.5, h: 0.2, color: 'E2E8F0', fontSize: 9 });
    slide12.addText('• 自动编辑文件、执行命令、编写代码', { x: 0.8, y: 2.05, w: 3.5, h: 0.2, color: 'E2E8F0', fontSize: 9 });
    slide12.addText('• 支持 Agent 模式，自主完成任务', { x: 0.8, y: 2.3, w: 3.5, h: 0.2, color: 'E2E8F0', fontSize: 9 });
    slide12.addText('• 与 VS Code 等 IDE 深度集成', { x: 0.8, y: 2.55, w: 3.5, h: 0.2, color: 'E2E8F0', fontSize: 9 });

    slide12.addText('学习资源推荐', { x: 4.8, y: 1, w: 5, h: 0.25, color: '1A365D', fontSize: 14, bold: true, border: { pt: 0, pb: 2, color: '4299E1' } });

    slide12.addShape(pptx.shapes.RECTANGLE, { x: 4.8, y: 1.4, w: 5, h: 0.9, fill: { color: 'FFFFFF' }, line: { color: '4299E1', pt: 2 } });
    slide12.addText('哔哩哔哩视频教程', { x: 4.9, y: 1.5, w: 4.8, h: 0.2, color: '1A365D', fontSize: 11, bold: true });
    slide12.addText('秋芝 2046 Agent Skills - 系统讲解 Claude Code 的使用技巧和最佳实践', { x: 4.9, y: 1.75, w: 4.8, h: 0.3, color: '4A5568', fontSize: 9 });
    slide12.addText('BV1G3FNznEiS', {
        x: 4.9, y: 2.05, w: 4.8, h: 0.15, color: '2B6CB0', fontSize: 9,
        hyperlink: { url: 'https://www.bilibili.com/video/BV1G3FNznEiS/', tooltip: '观看视频' }
    });

    slide12.addShape(pptx.shapes.RECTANGLE, { x: 4.8, y: 2.45, w: 5, h: 0.9, fill: { color: 'FFFFFF' }, line: { color: '4299E1', pt: 2 } });
    slide12.addText('配套图文指南', { x: 4.9, y: 2.55, w: 4.8, h: 0.2, color: '1A365D', fontSize: 11, bold: true });
    slide12.addText('详细的图文教程，覆盖安装配置、常用命令、实战案例等内容', { x: 4.9, y: 2.8, w: 4.8, h: 0.3, color: '4A5568', fontSize: 9 });
    slide12.addText('guide-app-lyart.vercel.app', {
        x: 4.9, y: 3.1, w: 4.8, h: 0.15, color: '2B6CB0', fontSize: 9,
        hyperlink: { url: 'https://guide-app-lyart.vercel.app/', tooltip: '查看指南' }
    });

    slide12.addShape(pptx.shapes.RECTANGLE, { x: 4.8, y: 3.5, w: 5, h: 0.4, fill: { color: 'C6F6D5' }, line: { color: '38A169', pt: 2 } });
    slide12.addText('建议：先观看视频建立整体认知，再查阅图文指南进行实操练习', { x: 4.9, y: 3.6, w: 4.8, h: 0.25, color: '2F855A', fontSize: 9 });

    console.log('✓ Slide 12: Claude Code 配置 (含可点击链接)');

    // Slide 13: 结束页
    await html2pptx(path.join(slidesDir, 'slide09.html'), pptx);
    console.log('✓ Slide 13: 结束页');

    const outputPath = path.join(__dirname, '漫谈VibeCoding-2026年4月.pptx');
    await pptx.writeFile({ fileName: outputPath });
    console.log(`\n✓ Presentation saved to: ${outputPath}`);
}

createPresentation().catch(error => {
    console.error('Error creating presentation:', error);
    process.exit(1);
});
