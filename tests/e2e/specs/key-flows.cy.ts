/**
 * 关键用户流程 E2E：登录、创建日程、进入聊天
 * 使用 cy.intercept 模拟后端，无需真实服务即可在 CI 中运行
 */
describe('关键流程 E2E', () => {
  const stubApi = () => {
    cy.intercept('HEAD', '**', { statusCode: 200 }).as('head')
    cy.intercept('GET', '**/getAllUser**', { fixture: 'user-list.json' }).as('getUserList')
    cy.intercept('POST', '**/auth/login**', { fixture: 'auth-login.json' }).as('login')
    cy.intercept('GET', '**/getAll**', { fixture: 'schedule-list.json' }).as('getScheduleList')
    cy.intercept('GET', '**/getData**', { fixture: 'get-save.json' }).as('getSave')
    cy.intercept('POST', '**/setData**', { fixture: 'schedule-save.json' }).as('setSave')
  }

  describe('登录流程', () => {
    beforeEach(() => {
      stubApi()
      cy.visit('/')
    })

    it('未登录时显示登录页', () => {
      cy.contains('用户登录').should('be.visible')
      cy.get('#btnUser').should('be.visible')
      cy.contains('登 录').should('be.visible')
    })

    it('选择用户、输入密码、登录后进入主界面', () => {
      cy.wait('@getUserList')
      cy.get('#btnUser').click()
      cy.get('ion-popover').should('be.visible')
      cy.get('ion-popover ion-radio').first().click()
      cy.get('ion-input').filter('[type="password"]').type('e2e-password', { force: true })
      cy.contains('ion-button', '登 录').click()
      cy.wait('@login')
      cy.get('ion-tab-bar').should('be.visible')
      cy.contains('日程浏览').should('be.visible')
      cy.contains('智能对话').should('be.visible')
    })
  })

  describe('创建日程', () => {
    beforeEach(() => {
      stubApi()
      cy.visit('/')
      cy.wait('@getUserList')
      cy.get('#btnUser').click()
      cy.get('ion-popover ion-radio').first().click()
      cy.get('ion-input').filter('[type="password"]').type('e2e-password', { force: true })
      cy.contains('ion-button', '登 录').click()
      cy.wait('@login')
      cy.get('ion-tab-bar').should('be.visible')
      cy.visit('/tabs/tab1')
      cy.wait('@getScheduleList')
    })

    it('点击 FAB 打开新增日程弹窗并保存', () => {
      cy.get('ion-button.rounded-full').click()
      cy.contains('新增日程').should('be.visible')
      cy.get('ion-modal ion-input').first().type('E2E测试日程', { force: true })
      cy.contains('ion-button', '保存').click()
      cy.wait('@setSave')
      cy.contains('新增日程').should('not.exist')
    })
  })

  describe('进入聊天', () => {
    beforeEach(() => {
      stubApi()
      cy.visit('/')
      cy.wait('@getUserList')
      cy.get('#btnUser').click()
      cy.get('ion-popover ion-radio').first().click()
      cy.get('ion-input').filter('[type="password"]').type('e2e-password', { force: true })
      cy.contains('ion-button', '登 录').click()
      cy.wait('@login')
      cy.get('ion-tab-bar').should('be.visible')
    })

    it('点击智能对话 Tab 进入聊天页', () => {
      cy.contains('ion-tab-button', '智能对话').click()
      cy.url().should('include', '/tabs/tab3')
      cy.contains('Tab Chat').should('be.visible')
      cy.contains('聊天室').should('be.visible')
    })
  })
})
