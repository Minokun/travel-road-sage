import { View, Text } from '@tarojs/components'
import './index.scss'

interface MarkdownProps {
  content: string
}

interface ParsedBlock {
  type: 'heading' | 'paragraph' | 'list' | 'code' | 'blockquote' | 'hr'
  level?: number
  items?: string[]
  content?: string
  language?: string
}

function parseInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // 粗体 **text** 或 __text__
    const boldMatch = remaining.match(/^(\*\*|__)(.+?)\1/)
    if (boldMatch) {
      nodes.push(<Text key={key++} className="md-bold">{boldMatch[2]}</Text>)
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }

    // 斜体 *text* 或 _text_
    const italicMatch = remaining.match(/^(\*|_)(.+?)\1/)
    if (italicMatch) {
      nodes.push(<Text key={key++} className="md-italic">{italicMatch[2]}</Text>)
      remaining = remaining.slice(italicMatch[0].length)
      continue
    }

    // 行内代码 `code`
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      nodes.push(<Text key={key++} className="md-inline-code">{codeMatch[1]}</Text>)
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }

    // 链接 [text](url)
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (linkMatch) {
      nodes.push(<Text key={key++} className="md-link">{linkMatch[1]}</Text>)
      remaining = remaining.slice(linkMatch[0].length)
      continue
    }

    // 普通文本（取到下一个特殊字符前）
    const textMatch = remaining.match(/^[^*_`\[]+/)
    if (textMatch) {
      nodes.push(<Text key={key++}>{textMatch[0]}</Text>)
      remaining = remaining.slice(textMatch[0].length)
      continue
    }

    // 如果没有匹配，取一个字符
    nodes.push(<Text key={key++}>{remaining[0]}</Text>)
    remaining = remaining.slice(1)
  }

  return nodes
}

function parseMarkdown(content: string): ParsedBlock[] {
  const lines = content.split('\n')
  const blocks: ParsedBlock[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // 空行跳过
    if (line.trim() === '') {
      i++
      continue
    }

    // 代码块 ```
    if (line.startsWith('```')) {
      const language = line.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      blocks.push({
        type: 'code',
        content: codeLines.join('\n'),
        language
      })
      i++
      continue
    }

    // 标题 # ## ### 等
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        content: headingMatch[2]
      })
      i++
      continue
    }

    // 分割线 --- 或 ***
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      blocks.push({ type: 'hr' })
      i++
      continue
    }

    // 引用 >
    if (line.startsWith('>')) {
      const quoteLines: string[] = []
      while (i < lines.length && lines[i].startsWith('>')) {
        quoteLines.push(lines[i].slice(1).trim())
        i++
      }
      blocks.push({
        type: 'blockquote',
        content: quoteLines.join('\n')
      })
      continue
    }

    // 无序列表 - 或 *
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''))
        i++
      }
      blocks.push({
        type: 'list',
        items
      })
      continue
    }

    // 有序列表 1. 2. 等
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''))
        i++
      }
      blocks.push({
        type: 'list',
        items
      })
      continue
    }

    // 普通段落
    blocks.push({
      type: 'paragraph',
      content: line
    })
    i++
  }

  return blocks
}

export default function Markdown({ content }: MarkdownProps) {
  const blocks = parseMarkdown(content)

  return (
    <View className="markdown">
      {blocks.map((block, index) => {
        switch (block.type) {
          case 'heading':
            return (
              <View key={index} className={`md-heading md-h${block.level}`}>
                <Text>{block.content}</Text>
              </View>
            )

          case 'paragraph':
            return (
              <View key={index} className="md-paragraph">
                {parseInline(block.content || '')}
              </View>
            )

          case 'list':
            return (
              <View key={index} className="md-list">
                {block.items?.map((item, idx) => (
                  <View key={idx} className="md-list-item">
                    <Text className="md-list-bullet">•</Text>
                    <View className="md-list-content">
                      {parseInline(item)}
                    </View>
                  </View>
                ))}
              </View>
            )

          case 'code':
            return (
              <View key={index} className="md-code-block">
                {block.language && (
                  <View className="md-code-lang">
                    <Text>{block.language}</Text>
                  </View>
                )}
                <Text className="md-code-content" selectable>
                  {block.content}
                </Text>
              </View>
            )

          case 'blockquote':
            return (
              <View key={index} className="md-blockquote">
                <Text>{block.content}</Text>
              </View>
            )

          case 'hr':
            return <View key={index} className="md-hr" />

          default:
            return null
        }
      })}
    </View>
  )
}
