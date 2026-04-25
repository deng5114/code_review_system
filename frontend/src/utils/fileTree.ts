import type { ProjectFile, ReviewIssue, TreeNode } from '../types'

export function buildFileTree(files: ProjectFile[], issues?: ReviewIssue[]): TreeNode[] {
  const issueCount = new Map<string, number>()
  if (issues) {
    for (const issue of issues) {
      issueCount.set(issue.file_path, (issueCount.get(issue.file_path) || 0) + 1)
    }
  }

  const root: TreeNode[] = []
  const map = new Map<string, TreeNode>()

  for (const file of files) {
    if (file.is_vendor || file.is_generated) continue
    const parts = file.file_path.split('/')
    let current = root
    let pathSoFar = ''

    for (let i = 0; i < parts.length; i++) {
      pathSoFar = pathSoFar ? `${pathSoFar}/${parts[i]}` : parts[i]

      if (i === parts.length - 1) {
        const count = issueCount.get(file.file_path) || 0
        const node: TreeNode = {
          key: file.id,
          title: count > 0 ? `${parts[i]} (${count})` : parts[i],
          isLeaf: true,
          data: { fileId: file.id, filePath: file.file_path, language: file.language, lineCount: file.line_count },
        }
        current.push(node)
      } else {
        if (!map.has(pathSoFar)) {
          const node: TreeNode = { key: pathSoFar, title: parts[i], children: [] }
          map.set(pathSoFar, node)
          current.push(node)
        }
        current = map.get(pathSoFar)!.children!
      }
    }
  }
  return root
}
